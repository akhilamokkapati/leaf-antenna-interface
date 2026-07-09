# 🍃 Leaf Antenna Design Interface

AI-assisted design front-end for a biomimetic **2.45 GHz "leaf" WiFi antenna**,
built for **30.102 EM 1D, Group 06**.

Tune six parameters by **chat** or **sliders**, press **Run**, and the app
re-runs an existing **CST Studio Suite 2025** parametric macro to regenerate the
geometry, solve, and read **S1,1 + gain** back into the UI. It also runs fully in
a **demo mode** with trend-faithful synthetic data, so you can develop and
rehearse the demo on any laptop with no CST installed.

The CST macro `leaf_antenna_parametric_cst2025.bas` **owns all geometry**. This
app never draws geometry - it only sets parameters and re-runs the macro.

---

## Quick start (teammates & professor)

**You need:** [Python 3.10+](https://python.org) (tick *"Add Python to PATH"* when installing). For live results you also need **CST Studio Suite 2025** installed.

1. **Get the files:** on the GitHub page, click green **Code -> Download ZIP**, then unzip. (Or `git clone` if you use git.)
2. **Double-click a launcher** (first run auto-installs everything, ~1 min):
   - **`run_cst.bat`** -> LIVE CST mode. Change parameters, press **Run**, and CST solves on *your* machine (~2 min/run) with real S1,1.
   - **`run_demo.bat`** -> instant demo mode, no CST needed (great for a quick look).
3. A browser tab opens at `http://localhost:8501`. Close the console window to stop.

If your CST is installed somewhere other than the default
`C:\Program Files (x86)\CST Studio Suite 2025\...`, set `CST_PY_PATH` (see the
"live CST mode" section below) or edit the constant at the top of `cst_link.py`.

---

## Features

- **Sliders** for all six macro parameters (`num_fin_pairs` steps by 1).
- **Chatbot**: "add 2 fins", "set leaf length to 80", "make it resonate lower",
  "deeper match", "reset". Uses Claude if `ANTHROPIC_API_KEY` is set, otherwise a
  built-in offline rule parser.
- **Run**: S1,1 plot (WiFi band shaded, −10 dB line, previous runs overlaid faded
  for fin-count comparison), metric cards (resonant freq vs 2.45 GHz, min S1,1,
  max gain), and a green/red "covers WiFi band" badge.
- **Auto-optimize**: searches for parameters resonant at 2.45 GHz with the
  deepest band-covering match; loads the winner into the sliders.
- **Live geometry preview** (illustrative sketch only).
- **CST macro expander**: a pasteable VBA `Sub Main()` (with `use_dxf_defaults=0`
  and `RunMacro`) to reproduce the design on a CST-only machine.
- **Run-history table** with CSV download.

---

## Parameters

| slider / CST name   | range      | default | effect                                   |
|---------------------|------------|---------|------------------------------------------|
| `num_fin_pairs`     | 3-8 (int)  | 4       | more fins → lower resonance + deeper match (macro clamps at 8) |
| `leaf_length`       | 60-90 mm   | 75.75   | longer → lower resonance (primary knob)  |
| `rim_width`         | 2-6 mm     | 4.2     | affects matching                         |
| `center_stem_width` | 2-6 mm     | 4.2     | feed/stem width, small freq effect       |
| `fin_width`         | 0.8-3 mm   | 1.4     | wider → deeper match                     |
| `leaf_ground_gap`   | 2-12 mm    | 5.0     | larger → detunes / shallower match       |

**Target:** resonance at 2.45 GHz, S1,1 ≤ −10 dB across 2.400-2.4835 GHz.

---

The UI is a **custom local web app** - a small standard-library Python server
(`server.py`, no web framework, no Streamlit) that serves `web/index.html` and
exposes the engine over a tiny JSON API.

## Install

```bash
pip install -r requirements.txt
```

Only `numpy` and `matplotlib` are required (`server.py` itself uses the Python
standard library). `anthropic` is optional - omit it and the chatbot uses the
offline rule parser.

---

## Run - demo mode (any laptop, no CST)

Demo mode is the **default**. Just:

```bash
python server.py
```

It starts a local server and opens `http://localhost:8501` in your browser.
Everything works (chat, sliders, S₁₁ chart, optimizer) using synthetic physics
whose *trends* match reality. Options: `python server.py --port 9000 --no-browser`.

If you used the bundled virtual environment, run it with that interpreter:

```powershell
.\.venv\Scripts\python server.py
```

Optional - enable the Claude-backed chatbot:

```powershell
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python server.py
```

---

## Run - live CST mode (Windows machine with CST Studio Suite 2025)

1. Put `leaf_antenna_parametric_cst2025.bas` in this folder, and open/create the
   CST project (`.cst`) that contains it.
2. Set the environment variables, then launch:

```powershell
$env:DEMO_MODE   = "false"
$env:PROJECT_PATH = "C:\path\to\leaf_antenna.cst"
$env:CST_PY_PATH  = "C:\Program Files (x86)\CST Studio Suite 2025\AMD64\python_cst_libraries"
# optional
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python server.py
```

In live mode, pressing **Run** will:
`use_dxf_defaults=0` → `StoreParameter` each value → `RunMacro` (regenerate
geometry) → `run_solver()` → read `1D Results\S-Parameters\S1,1` and max gain.

### If a CST API call errors on your machine
Every CST call is wrapped so a missing/mismatched API can never crash the app -
you'll see a clean error in the UI. The CST-specific strings are all constants at
the top of [`cst_link.py`](cst_link.py):

- `S11_RESULT_PATH` - the S-parameter result tree path.
- `GAIN_RESULT_PATHS` - candidate farfield max-gain paths (verify against your
  project's result tree; a miss just leaves gain blank).
- `MACRO_NAME`, `PROJECT_PATH`, `CST_PY_PATH`.

Fixes are one-liners there.

---

## Project structure

```
leaf-antenna-interface/
  server.py       # local web server (stdlib only) + JSON API  ← run this
  web/index.html  # custom single-page UI (HTML/CSS/JS, no framework)
  cst_link.py     # CST driver + VBA generator + demo physics + analysis
  chatbot.py      # natural language -> parameter changes (Claude + rule fallback)
  geometry.py     # matplotlib leaf sketch (preview only)
  optimizer.py    # auto-tune search to hit 2.45 GHz
  requirements.txt
  README.md
  leaf_antenna_parametric_cst2025.bas   # your macro (drop it in)
```

---

## Notes

- The geometry preview is **illustrative** - it is not the simulated geometry.
- The demo physics model is intentionally simple but trend-faithful; do not quote
  its numbers as CST results. Use live CST mode for real S-parameters.
