"""
cst_link.py - CST driver + VBA generator + demo fallback.

This module is the ONLY place that talks to CST Studio Suite. Everything else
(the UI, the chatbot, the optimizer) goes through:

    run_simulation(params) -> (freqs_GHz, s11_dB, gain_dBi_or_None)
    generate_vba(params)   -> pasteable VBA Sub Main() text
    analyse(freqs, s11_dB) -> dict of headline metrics

The CST macro `leaf_antenna_parametric_cst2025.bas` OWNS all geometry. This app
never draws geometry into CST - it only sets parameters and re-runs the macro.

DEMO_MODE lets the whole app run (chat, sliders, plots, optimizer) on any laptop
with no CST installed, using a small synthetic physics model whose *trends* match
reality. Flip DEMO_MODE to False on the CST machine.
"""

from __future__ import annotations

import os
import sys
import numpy as np

# ---------------------------------------------------------------------------
# Mode + machine-specific paths (override via environment variables)
# ---------------------------------------------------------------------------
# DEMO_MODE=True  -> synthetic data, no CST needed (default, safe for any laptop)
# DEMO_MODE=False -> drive real CST. Set PROJECT_PATH + CST_PY_PATH as well.
def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


DEMO_MODE = _env_flag("DEMO_MODE", True)

_HERE = os.path.dirname(os.path.abspath(__file__))

# Working .cst project the app drives. It is created fresh from the macro on the
# first live run (a dedicated sandbox - your other .cst files are never touched).
PROJECT_PATH = os.environ.get("PROJECT_PATH", os.path.join(_HERE, "leaf_live.cst"))

# The parametric VBA macro (owns all geometry). Executed via `RunScript`.
BAS_PATH = os.environ.get("BAS_PATH", os.path.join(_HERE, "leaf_antenna_parametric_cst2025.bas"))

# CST 2025 Python libraries (adjust if CST is installed elsewhere).
CST_PY_PATH = os.environ.get(
    "CST_PY_PATH",
    r"C:\Program Files (x86)\CST Studio Suite 2025\AMD64\python_cst_libraries",
)

MACRO_NAME = "leaf_antenna_parametric_cst2025"

# --- CST result-tree strings (verified live on CST 2025.4) ---
# The macro makes ONE discrete port, so S-results live at S1,1.
S11_RESULT_PATH = r"1D Results\S-Parameters\S1,1"
# Total efficiency (0..1) is shown in place of a farfield gain figure, which
# would need the (memory-heavy) field monitors we drop for laptop solving.
EFFICIENCY_RESULT_PATH = r"1D Results\Efficiencies\Tot. Efficiency [1]"

# The default macro sets up E/H 3D field monitors + leaves the time-domain
# solver active, which needs ~160 GB RAM. We drop those monitors and switch to
# the frequency-domain solver (tetrahedral mesh) so it solves on a laptop in
# ~1.5 min. This VBA runs in history right AFTER the macro, every rebuild.
_FD_SETUP_VBA = (
    'On Error Resume Next\n'
    'Monitor.Delete "e_field_2p45"\n'
    'Monitor.Delete "h_field_2p45"\n'
    'On Error GoTo 0\n'
    'ChangeSolverType "HF Frequency Domain"'
)

# --- Auto fin-spacing --------------------------------------------------------
# The macro places fins center-out at `alternating_fin_spacing`, clamped to
# [fin_start_x, fin_end_x]. With the macro default (9.91 mm) high fin counts
# overflow and pile onto the tip (e.g. 7 fins -> only 6 distinct). We compute a
# spacing that keeps all N fins distinct inside the fin region, but never widen
# past the macro default (so low counts keep the team's nominal design).
FIN_CENTER_X = 39.66          # macro default alternating_fin_center_x
FIN_START_X = 14.47           # macro default fin_start_x
FIN_END_X = 56.45             # macro default fin_end_x
FIN_DEFAULT_SPACING = 9.91    # macro default alternating_fin_spacing


def _fin_positions(n: int, sp: float) -> list:
    """Replicates the macro's AlternatingFinX() clamping for n fins at spacing sp."""
    xs = []
    for i in range(1, int(n) + 1):
        if i <= 1:
            x = FIN_CENTER_X
        else:
            off = i // 2
            d = 1.0 if i % 2 == 0 else -1.0
            x = FIN_CENTER_X + d * sp * off
        xs.append(round(max(FIN_START_X, min(FIN_END_X, x)), 3))
    return xs


def auto_fin_spacing(n: int) -> float:
    """Fin spacing (mm) that makes `n` distinct fins. Keeps the macro default
    when it already yields n distinct; otherwise shrinks to fit the fin region."""
    n = int(n)
    if len(set(_fin_positions(n, FIN_DEFAULT_SPACING))) == n:
        return FIN_DEFAULT_SPACING
    plus_max, minus_max = n // 2, (n - 1) // 2
    cand = []
    if plus_max:
        cand.append((FIN_END_X - FIN_CENTER_X) / plus_max)
    if minus_max:
        cand.append((FIN_CENTER_X - FIN_START_X) / minus_max)
    fit = (min(cand) * 0.96) if cand else FIN_DEFAULT_SPACING
    return round(fit, 3)


def _cst_overrides(params: dict) -> dict:
    """Name->string map the app pushes to CST: the six sliders + auto fin spacing
    so `num_fin_pairs` always renders as that many distinct fins."""
    out = {}
    for k in PARAM_ORDER:
        v = params[k]
        out[k] = str(int(v)) if k == "num_fin_pairs" else f"{float(v):g}"
    out["alternating_fin_spacing"] = f"{auto_fin_spacing(params['num_fin_pairs']):g}"
    return out

# ---------------------------------------------------------------------------
# Parameter specification - the single source of truth for names/ranges/steps.
# (slider key == CST parameter name for all six.)
# ---------------------------------------------------------------------------
# Each entry: (min, max, default, step, unit, one-line effect)
PARAM_SPEC = {
    "num_fin_pairs":     (3,    8,    4,     1,    "",   "more fins -> lower resonance + deeper match (macro clamps at 8)"),
    "leaf_length":       (60.0, 90.0, 75.75, 0.25, "mm", "longer -> lower resonance (primary frequency knob)"),
    "rim_width":         (2.0,  6.0,  4.2,   0.1,  "mm", "affects matching (best near 4.2)"),
    "center_stem_width": (2.0,  6.0,  4.2,   0.1,  "mm", "feed/stem width, small frequency effect"),
    "fin_width":         (0.8,  3.0,  1.4,   0.1,  "mm", "wider -> deeper match"),
    "leaf_ground_gap":   (2.0,  12.0, 5.0,   0.5,  "mm", "larger -> detunes / shallower match"),
}

PARAM_ORDER = list(PARAM_SPEC.keys())

# WiFi 2.4 GHz band edges (GHz) and design target.
WIFI_BAND = (2.400, 2.4835)
TARGET_FREQ = 2.45  # GHz


def defaults() -> dict:
    """Return a fresh dict of default parameter values."""
    return {k: PARAM_SPEC[k][2] for k in PARAM_ORDER}


def clip_param(name: str, value) -> float | int:
    """Clip a single parameter to its range and snap to its step.

    num_fin_pairs is forced to an int; everything else is rounded to its step
    so slider state and chat edits stay consistent.
    """
    lo, hi, _default, step, _unit, _eff = PARAM_SPEC[name]
    try:
        value = float(value)
    except (TypeError, ValueError):
        return PARAM_SPEC[name][2]
    value = max(lo, min(hi, value))
    if name == "num_fin_pairs":
        return int(round(value))
    # snap to step grid, then round to a sane number of decimals
    snapped = round(value / step) * step
    return round(snapped, 3)


def clip_all(params: dict) -> dict:
    """Clip every known parameter; ignore unknown keys."""
    out = defaults()
    for k, v in params.items():
        if k in PARAM_SPEC:
            out[k] = clip_param(k, v)
    return out


# ---------------------------------------------------------------------------
# Demo physics model (synthetic but trend-faithful). Used when DEMO_MODE=True.
# ---------------------------------------------------------------------------
def _demo_resonance_and_depth(params: dict) -> tuple[float, float]:
    """Return (f0_GHz, match_depth_dB) from the parameter set.

    Trends (see project spec):
      - f0 scales as reference_length / leaf_length (longer leaf -> lower freq)
      - each fin above 4 nudges f0 down ~0.6%
      - wider stem nudges f0 slightly up
      - match depth grows with fin count and fin_width, and degrades as
        rim_width departs from its 4.2 optimum and as ground gap exceeds 5.
    """
    fins = params["num_fin_pairs"]
    leaf_length = params["leaf_length"]
    rim_width = params["rim_width"]
    stem = params["center_stem_width"]
    fin_width = params["fin_width"]
    gap = params["leaf_ground_gap"]

    ref_len = PARAM_SPEC["leaf_length"][2]  # 75.75 mm
    f0 = TARGET_FREQ * (ref_len / leaf_length)
    f0 *= (1.0 - 0.006 * (fins - 4))          # capacitive loading from fins
    f0 *= (1.0 + 0.004 * (stem - 4.2))        # wider stem -> slightly higher

    # Match depth (dB, positive number = how deep the dip is below 0 dB).
    depth = 12.0
    depth += 2.2 * (fins - 4)                  # more fins -> deeper
    depth += 6.0 * (fin_width - 1.4)           # wider fin -> deeper
    depth -= 3.0 * abs(rim_width - 4.2)        # rim off-optimum -> shallower
    depth -= 1.6 * max(0.0, gap - 5.0)         # big ground gap -> shallower
    depth = float(np.clip(depth, 5.0, 32.0))
    return float(f0), depth


def _demo_s11_curve(params: dict, freqs: np.ndarray) -> np.ndarray:
    """Lorentzian dip at f0 with small noise, returned in dB (negative)."""
    f0, depth = _demo_resonance_and_depth(params)
    # Bandwidth of the dip: deeper/higher-Q dips are a touch narrower.
    hwhm = 0.045  # GHz half-width at half-max, roughly WiFi-band scale
    lorentz = depth / (1.0 + ((freqs - f0) / hwhm) ** 2)
    s11 = -lorentz  # dip below 0 dB
    rng = np.random.default_rng(_seed_from_params(params))
    s11 = s11 + rng.normal(0.0, 0.15, size=freqs.shape)  # small measurement noise
    return s11


def _seed_from_params(params: dict) -> int:
    """Deterministic seed so the same params always give the same demo curve."""
    key = tuple(round(float(params[k]), 3) for k in PARAM_ORDER)
    return abs(hash(key)) % (2**32)


def _demo_gain(params: dict) -> float:
    """gain ~= 1.8 + 0.12*(fins-4) dBi."""
    return round(1.8 + 0.12 * (params["num_fin_pairs"] - 4), 2)


# ---------------------------------------------------------------------------
# Public: run a simulation (demo or live)
# ---------------------------------------------------------------------------
def run_simulation(params: dict) -> tuple[np.ndarray, np.ndarray, float | None]:
    """Return (freqs_GHz, s11_dB, gain_dBi_or_None) for the given parameters.

    In DEMO_MODE this is instant and synthetic. Otherwise it drives CST. Any
    CST failure raises RuntimeError with a clean message for the UI to show.
    """
    params = clip_all(params)
    if DEMO_MODE:
        freqs = np.linspace(2.2, 2.7, 501)
        s11 = _demo_s11_curve(params, freqs)
        gain = _demo_gain(params)
        return freqs, s11, gain
    return _run_cst(params)


# --- persistent CST session (created once, reused across runs) -------------
import threading

_CST = {"de": None, "prj": None, "m3d": None}
_CST_LOCK = threading.RLock()   # serialize CST access (not thread-safe)


def _cst_session():
    """Return (de, prj, model3d), creating a fresh sandbox project on first use.

    The macro RunScript + FD-solver setup are added to the project history ONCE.
    Thereafter each run only updates parameters and rebuilds the history, so the
    macro isn't stacked up repeatedly.
    """
    if _CST["m3d"] is not None:
        return _CST["de"], _CST["prj"], _CST["m3d"]

    try:
        if CST_PY_PATH not in sys.path:
            sys.path.append(CST_PY_PATH)
        import cst.interface  # type: ignore
        import cst.results    # noqa: F401  (imported to validate availability)
    except Exception as exc:
        raise RuntimeError(
            f"Could not import CST Python libraries from '{CST_PY_PATH}'. "
            f"Set CST_PY_PATH or run in DEMO_MODE. ({exc})"
        )

    try:
        de = cst.interface.DesignEnvironment.connect_to_any_or_new()
        de.set_quiet_mode(True)  # block GUI pop-ups during automation
    except Exception as exc:
        raise RuntimeError(f"Could not start/connect to CST. ({exc})")

    # Close any already-open copy of OUR sandbox project (frees the file lock)
    # without touching the user's other projects, then delete the stale files.
    try:
        base = os.path.basename(PROJECT_PATH).lower()
        for ident in list(de.list_open_projects()):
            if base in str(ident).lower() or "leaf_live" in str(ident).lower():
                try:
                    de.get_open_project(ident).close()
                except Exception:
                    pass
    except Exception:
        pass
    try:
        if os.path.exists(PROJECT_PATH):
            os.remove(PROJECT_PATH)
        _folder = os.path.splitext(PROJECT_PATH)[0]
        if os.path.isdir(_folder):
            import shutil
            shutil.rmtree(_folder, ignore_errors=True)
    except Exception:
        pass  # a locked stale file is non-fatal; save may still succeed

    try:
        prj = de.new_mws()
        m = prj.model3d
        # Seed defaults with use_dxf_defaults=0 so our overrides always survive.
        m.StoreParameter("use_dxf_defaults", "0")
        # History block 1: run the parametric macro (owns all geometry).
        m.add_to_history("run leaf macro", f'RunScript "{BAS_PATH}"')
        # History block 2: laptop-friendly solver setup (runs after the macro).
        m.add_to_history("fd solver setup", _FD_SETUP_VBA)
        prj.save(PROJECT_PATH, True)
    except Exception as exc:
        raise RuntimeError(f"Could not create the CST working project. ({exc})")

    _CST.update(de=de, prj=prj, m3d=m)
    return de, prj, m


def _run_cst(params: dict) -> tuple[np.ndarray, np.ndarray, float | None]:
    """Drive real CST: set params -> rebuild geometry -> FD solve -> read S1,1.

    Serialized with a lock (CST isn't thread-safe). Any failure raises
    RuntimeError with a clean, UI-friendly message.
    """
    with _CST_LOCK:
        de, prj, m = _cst_session()   # ensures CST_PY_PATH is on sys.path
        import cst.results  # type: ignore  (importable now)

        # Re-assert quiet mode on every run. This lets you freely switch CST to
        # Interactive Mode to inspect/zoom the 3D model between runs; the app
        # snaps it back to quiet mode here so the solve won't hang on a dialog.
        try:
            de.set_quiet_mode(True)
        except Exception:
            pass

        # Push the six parameters + auto fin spacing (use_dxf_defaults pinned 0).
        try:
            for k, v_str in _cst_overrides(params).items():
                m.StoreParameter(k, v_str)
        except Exception as exc:
            raise RuntimeError(f"Failed to set parameters in CST. ({exc})")

        # Rebuild geometry from history with the new parameters, then solve.
        try:
            m.full_history_rebuild()
        except Exception as exc:
            raise RuntimeError(f"CST geometry rebuild failed. ({exc})")
        try:
            prj.save(PROJECT_PATH, True)
            m.run_solver()          # blocks (~1.5 min, frequency-domain solver)
            prj.save(PROJECT_PATH, True)
        except Exception as exc:
            raise RuntimeError(f"CST solve failed. ({exc})")

        # Read S1,1.
        try:
            pf = cst.results.ProjectFile(PROJECT_PATH, allow_interactive=True)
            d3 = pf.get_3d()
            item = d3.get_result_item(S11_RESULT_PATH)
            freqs = np.asarray(item.get_xdata(), dtype=float)          # GHz
            s11_complex = np.asarray(item.get_ydata(), dtype=complex)  # linear
            s11_db = 20.0 * np.log10(np.maximum(np.abs(s11_complex), 1e-12))
        except Exception as exc:
            raise RuntimeError(
                f"Solve finished but reading S1,1 from '{S11_RESULT_PATH}' failed. ({exc})"
            )

        # Total efficiency (0..1) reported in the gain slot (real gain would need
        # the heavy field monitors we drop). Tolerate absence -> None.
        gain = None
        try:
            eff = d3.get_result_item(EFFICIENCY_RESULT_PATH)
            vals = np.abs(np.asarray(eff.get_ydata(), dtype=float))
            if vals.size:
                gain = float(np.max(vals))  # peak total efficiency (0..1)
        except Exception:
            gain = None

        return freqs, s11_db, gain


# ---------------------------------------------------------------------------
# VBA generation (for the "reproduce on a CST-only machine" expander)
# ---------------------------------------------------------------------------
def _vba_store_block(params: dict) -> str:
    """StoreParameter lines (the six sliders + auto fin spacing), with
    use_dxf_defaults forced to 0 first."""
    lines = ['StoreParameter("use_dxf_defaults", "0")']
    for k, v_str in _cst_overrides(params).items():
        lines.append(f'StoreParameter("{k}", "{v_str}")')
    return "\n".join(lines)


def generate_vba(params: dict) -> str:
    """Return a complete, pasteable VBA Sub Main() that sets the params and
    re-runs the macro. Paste this into CST's VBA macro editor (Home > Macros >
    Edit/Debug) on a machine that has the project open.
    """
    params = clip_all(params)
    store = _vba_store_block(params)
    indented = "\n".join("    " + ln for ln in store.splitlines())
    return (
        "' Auto-generated by the Leaf Antenna Interface.\n"
        "' Sets the six leaf parameters, then re-runs the parametric macro.\n"
        "' use_dxf_defaults is forced to 0 so these values are NOT wiped.\n"
        "Sub Main()\n"
        f"{indented}\n"
        f'    RunMacro "{MACRO_NAME}"\n'
        "End Sub\n"
    )


# ---------------------------------------------------------------------------
# Analysis of an S11 sweep
# ---------------------------------------------------------------------------
def analyse(freqs: np.ndarray, s11_db: np.ndarray) -> dict:
    """Headline metrics from an S11 sweep.

    Returns: resonant_freq (GHz, the deepest dip), min_s11 (dB, most negative),
    band_edges (low, high) where S11 crosses -10 dB around resonance (or None),
    covers_wifi_band (bool: is S11 <= -10 dB across 2.400-2.4835 GHz).
    """
    freqs = np.asarray(freqs, dtype=float)
    s11_db = np.asarray(s11_db, dtype=float)

    i_min = int(np.argmin(s11_db))
    resonant_freq = float(freqs[i_min])
    min_s11 = float(s11_db[i_min])

    # -10 dB band edges: walk left/right from the dip until we cross -10 dB.
    band_low = band_high = None
    if min_s11 <= -10.0:
        j = i_min
        while j > 0 and s11_db[j] <= -10.0:
            j -= 1
        band_low = float(freqs[j])
        j = i_min
        while j < len(freqs) - 1 and s11_db[j] <= -10.0:
            j += 1
        band_high = float(freqs[j])

    # Does the whole WiFi band sit at or below -10 dB?
    mask = (freqs >= WIFI_BAND[0]) & (freqs <= WIFI_BAND[1])
    covers = bool(mask.any() and np.all(s11_db[mask] <= -10.0))

    return {
        "resonant_freq": resonant_freq,
        "min_s11": min_s11,
        "band_edges": None if band_low is None else (band_low, band_high),
        "covers_wifi_band": covers,
    }


def status_banner() -> str:
    """Short human-readable mode string for the UI banner."""
    if DEMO_MODE:
        return "DEMO MODE - synthetic data (no CST). Trends are physically faithful."
    return f"LIVE CST MODE - project: {PROJECT_PATH}"
