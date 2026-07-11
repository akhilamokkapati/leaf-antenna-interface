"""
precompute_cst.py - run a real CST sweep and cache the S11 curves.

Sweeps the two most influential knobs (num_fin_pairs x leaf_length) with the
other parameters at default, solving each in real CST, and writes the actual
results to cst_cache.json. The app then serves these REAL curves in demo/cloud
mode (nearest design), so the public link shows genuine CST data - not synthetic.

Robust: saves after every solve and skips already-done points, so if CST crashes
you can just re-run this and it resumes.

Run:  python precompute_cst.py
"""
import os, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["DEMO_MODE"] = "false"          # force the real CST path
sys.path.insert(0, HERE)

import numpy as np
import cst_link

# Grid: 6 fin counts x 3 leaf lengths = 18 real solves (~2 min each).
FINS = [3, 4, 5, 6, 7, 8]
LEAVES = [70.0, 75.75, 82.0]

OUT = os.path.join(HERE, "cst_cache.json")
cache = []
if os.path.exists(OUT):
    try:
        cache = json.load(open(OUT, encoding="utf-8"))
    except Exception:
        cache = []
done = {(round(c["params"]["num_fin_pairs"]), round(c["params"]["leaf_length"], 2)) for c in cache}

total = len(FINS) * len(LEAVES)
i = 0
t0 = time.time()
for fins in FINS:
    for leaf in LEAVES:
        i += 1
        key = (fins, round(leaf, 2))
        if key in done:
            print(f"[{i}/{total}] skip {key} (already cached)", flush=True)
            continue
        p = cst_link.defaults()
        p["num_fin_pairs"] = fins
        p["leaf_length"] = leaf
        print(f"[{i}/{total}] solving fins={fins} leaf={leaf} ...", flush=True)
        ts = time.time()
        try:
            f, s, g = cst_link.run_simulation(p)[:3]
            cache.append({
                "params": cst_link.clip_all(p),
                "freqs": np.asarray(f, float).round(5).tolist(),
                "s11_db": np.asarray(s, float).round(3).tolist(),
                "gain": None if g is None else round(float(g), 4),
            })
            json.dump(cache, open(OUT, "w", encoding="utf-8"))
            a = cst_link.analyse(np.asarray(f), np.asarray(s))
            print(f"   OK in {time.time()-ts:.0f}s  f_res={a['resonant_freq']:.3f} "
                  f"min_s11={a['min_s11']:.1f}  saved ({len(cache)} total)", flush=True)
        except Exception as e:
            print(f"   FAIL: {str(e)[:140]}", flush=True)

print(f"DONE: {len(cache)}/{total} points in {(time.time()-t0)/60:.1f} min -> {OUT}", flush=True)
