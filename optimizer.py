"""
optimizer.py - auto-tune search to hit 2.45 GHz with a deep, band-covering match.

The optimizer is generic: it takes an `evaluate_fn(params) -> (freqs, s11_db, gain)`
and minimizes a scalar `objective(analysis)` (lower is better), so it works the
same in demo mode (fast synthetic evals) and live CST mode (slow, budgeted).

Strategy: budget-aware COORDINATE search. We scan one parameter at a time,
keeping the best value found, and repeat for a couple of passes. This is far more
sample-efficient than a random grid (important when each live CST eval costs
minutes) and gives the primary frequency knob (leaf_length) fine resolution.
"""

from __future__ import annotations

import numpy as np

from cst_link import PARAM_SPEC, PARAM_ORDER, clip_all, TARGET_FREQ, analyse


# ---------------------------------------------------------------------------
# Objective - lower is better. Tweak here.
# ---------------------------------------------------------------------------
def objective(analysis: dict) -> float:
    """Penalise off-target resonance and a shallow match.

    - abs(f_res - 2.45) * 1000     -> ~1 point per MHz of frequency error
    - max(0, s11_min - (-10))       -> penalty ONLY when the dip is shallower than
                                       -10 dB. s11_min is negative; a shallow match
                                       (e.g. -3 dB) gives +7, a deep one (-25 dB)
                                       gives 0. (The naive `-10 - s11_min` form is
                                       backwards - it would reward shallow dips.)
    - +5 if the full WiFi band isn't covered, to nudge toward band coverage.
    """
    f_res = analysis["resonant_freq"]
    s11_min = analysis["min_s11"]
    score = abs(f_res - TARGET_FREQ) * 1000.0
    score += max(0.0, s11_min - (-10.0))   # shallow-match penalty (0 when <= -10 dB)
    if not analysis["covers_wifi_band"]:
        score += 5.0
    return float(score)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def optimize(
    evaluate_fn,
    start_params: dict,
    include_all: bool = False,
    budget: int | None = None,
    progress_cb=None,
):
    """Coordinate search minimizing `objective`.

    Args:
        evaluate_fn: params -> (freqs_GHz, s11_dB, gain). Usually cst_link.run_simulation.
        start_params: current parameter dict; the search starts from here and
                      holds non-searched params fixed at these values.
        include_all: True -> search all 6 params (demo). False -> search only the
                     two most influential (leaf_length, num_fin_pairs), right for
                     slow live CST evals.
        budget: hard cap on the number of (unique) evaluations. Defaults: 200
                (demo/all) or 12 (live/2-param). Live CST evals cost minutes each.
        progress_cb: optional callable(done, total, best_score) for UI progress.

    Returns:
        dict: {"params", "analysis", "score", "freqs", "s11_db", "gain", "evals"}
    """
    base = clip_all(start_params)

    if include_all:
        search_keys = PARAM_ORDER
        default_budget = 400   # demo evals are instant, so we can afford a lot
    else:
        # leaf_length + num_fin_pairs are the two most influential knobs.
        search_keys = ["leaf_length", "num_fin_pairs"]
        default_budget = 12
    if budget is None:
        budget = default_budget

    axes = {k: _axis_for(k) for k in search_keys}
    # Coarse leaf axis used INSIDE the joint (fins x leaf) scan, so that scan
    # doesn't devour the budget; leaf_length is then refined finely in the
    # coordinate pass. ~2 mm steps here vs ~1 mm in the fine axis.
    joint_leaf_axis = _axis_for("leaf_length", n=16) if "leaf_length" in axes else []

    # Cache keyed on the full 6-tuple so repeated params don't re-solve (this is
    # what makes the eval budget meaningful on live CST).
    cache: dict = {}

    def evaluate(params: dict) -> dict:
        params = clip_all(params)
        key = tuple(params[k] for k in PARAM_ORDER)
        if key in cache:
            return cache[key]
        freqs, s11_db, gain = evaluate_fn(params)
        ana = analyse(freqs, s11_db)
        res = {
            "params": params, "analysis": ana, "score": objective(ana),
            "freqs": freqs, "s11_db": s11_db, "gain": gain,
        }
        cache[key] = res
        return res

    # In this design more fins BOTH deepen the match AND detune it, so hitting
    # 2.45 GHz with full-band coverage needs a *simultaneous* (fins, leaf_length)
    # move that one-at-a-time coordinate search can't discover. When the budget
    # can afford it, scan that coupled pair jointly; the other four (weakly
    # coupled) params stay on cheap coordinate search. Tiny live budgets skip the
    # joint scan and use pure coordinate search, which is far more eval-efficient.
    coupled = [k for k in ("num_fin_pairs", "leaf_length") if k in search_keys]
    joint_cost = len(axes["num_fin_pairs"]) * len(joint_leaf_axis) if len(coupled) == 2 else 1
    do_joint = len(coupled) == 2 and budget >= joint_cost + len(search_keys)
    # When joint-scanning, num_fin_pairs is owned by the joint scan; leaf_length
    # is still coordinate-refined finely for frequency. The other params stay on
    # coordinate search either way.
    coord_keys = [k for k in search_keys if not (do_joint and k == "num_fin_pairs")]

    # Coverage in this model needs fins, fin_width AND leaf_length to move
    # together (a 3-way coupling), so a search from a single start can deadlock in
    # a local optimum. We therefore MULTI-START from a few design-space corners
    # plus the user's current design, all sharing one cache and budget. The final
    # answer is the best point in the cache, so no eval is ever wasted. (For the
    # tiny-budget live/2-param case we keep a single start — multi-start would
    # just fragment the budget.)
    passes = 3
    per_pass = (joint_cost if do_joint else 0) + sum(len(axes[k]) for k in coord_keys)
    total_est = min(budget, passes * max(per_pass, 1))
    best_seen = [float("inf")]  # best score across the whole run (for progress)

    def run_passes(start_result):
        """Joint + coordinate passes from one starting point (mutates cache)."""
        best = start_result
        for _pass in range(passes):
            improved = False
            scans = []
            if do_joint:
                scans.append(("joint", None))
            scans += [("coord", k) for k in coord_keys]

            for kind, k in scans:
                local_best = best
                combos = (
                    [(f, l) for f in axes["num_fin_pairs"] for l in joint_leaf_axis]
                    if kind == "joint" else [(k, v) for v in axes[k]]
                )
                for a, b in combos:
                    if len(cache) >= budget:
                        return  # budget exhausted; cache already holds all results
                    cand = dict(best["params"])
                    if kind == "joint":
                        cand["num_fin_pairs"], cand["leaf_length"] = a, b
                    else:
                        cand[a] = b
                    r = evaluate(cand)
                    best_seen[0] = min(best_seen[0], r["score"])
                    if progress_cb:
                        progress_cb(min(len(cache), total_est), total_est, best_seen[0])
                    if r["score"] < local_best["score"]:
                        local_best = r
                if local_best["score"] < best["score"]:
                    best = local_best
                    improved = True
            if not improved:
                break

    for seed in _seeds(base, do_joint):
        if len(cache) >= budget:
            break
        run_passes(evaluate(seed))

    # Best point found anywhere during the search.
    best = min(cache.values(), key=lambda r: r["score"])
    result = dict(best)
    result["evals"] = len(cache)
    return result


def _seeds(base: dict, multi: bool):
    """Starting points for the search.

    Single start (base) unless we're doing the full joint search with budget to
    spare, in which case we add design-space corners so multi-start can escape
    local optima: a max-depth corner (many wide fins), a high-frequency corner
    (few narrow fins, short leaf), and the parameter-space centre (defaults).
    """
    from cst_link import defaults as _defaults
    if not multi:
        return [clip_all(base)]
    d = _defaults()
    deep = {**d, "num_fin_pairs": 8, "fin_width": 3.0, "rim_width": 4.2,
            "center_stem_width": 4.2, "leaf_ground_gap": 2.0}     # deepest match
    high = {**d, "num_fin_pairs": 3, "fin_width": 1.0, "leaf_length": 64.0}  # high freq
    seeds, seen = [], set()
    for s in (clip_all(base), deep, d, high):
        key = tuple(s[k] for k in PARAM_ORDER)
        if key not in seen:
            seen.add(key)
            seeds.append(s)
    return seeds


def _axis_for(key: str, n: int | None = None):
    """Candidate values to scan for one parameter.

    num_fin_pairs is enumerated over its integer range; leaf_length (the primary
    frequency knob) defaults to ~1 mm resolution; other continuous params get a
    coarser grid. `n` overrides the sample count (used for the coarse joint-scan
    leaf axis). Values are snapped to each parameter's step via clip.
    """
    from cst_link import clip_param
    lo, hi, _d, _step, _u, _e = PARAM_SPEC[key]
    if key == "num_fin_pairs":
        return list(range(int(lo), int(hi) + 1))
    if n is None:
        n = 31 if key == "leaf_length" else 13
    return sorted({clip_param(key, v) for v in np.linspace(lo, hi, n)})
