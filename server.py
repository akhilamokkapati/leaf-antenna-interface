"""
server.py - lightweight local web server for the Leaf Antenna Interface.

A dependency-free (Python standard library only) replacement for the Streamlit
UI. It serves a custom single-page front-end (web/index.html) and exposes the
existing, tested engine (cst_link / chatbot / optimizer / geometry) over a small
JSON API. No Streamlit, no framework, nothing to pip-install beyond what the
engine already needs (numpy, matplotlib; anthropic optional).

Run:  python server.py            (opens http://localhost:8501)
      python server.py --port 9000 --no-browser
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import cst_link
from cst_link import (
    PARAM_SPEC, PARAM_ORDER, defaults, clip_all, run_simulation, generate_vba,
    analyse, WIFI_BAND, TARGET_FREQ, status_banner,
)
import chatbot
import optimizer
import geometry

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")


# ---------------------------------------------------------------------------
# JSON-serialisable helpers
# ---------------------------------------------------------------------------
def _sim_payload(params: dict) -> dict:
    """Run a simulation and package everything the UI needs as plain JSON."""
    freqs, s11_db, gain = run_simulation(params)
    ana = analyse(freqs, s11_db)
    return {
        "params": clip_all(params),
        "freqs": np.asarray(freqs, dtype=float).round(5).tolist(),
        "s11_db": np.asarray(s11_db, dtype=float).round(4).tolist(),
        "gain": None if gain is None else round(float(gain), 3),
        "analysis": ana,
    }


def _geometry_png(params: dict) -> str:
    """Render the leaf sketch to a transparent base64 PNG (data-URI body)."""
    fig = geometry.draw_leaf(clip_all(params))
    fig.patch.set_alpha(0.0)  # transparent so it blends into the card
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, transparent=True, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _config() -> dict:
    spec = {}
    for k in PARAM_ORDER:
        lo, hi, dflt, step, unit, eff = PARAM_SPEC[k]
        spec[k] = {"min": lo, "max": hi, "default": dflt, "step": step,
                   "unit": unit, "effect": eff, "is_int": k == "num_fin_pairs"}
    return {
        "demo_mode": cst_link.DEMO_MODE,
        "banner": status_banner(),
        "spec": spec,
        "order": PARAM_ORDER,
        "defaults": defaults(),
        "wifi_band": list(WIFI_BAND),
        "target": TARGET_FREQ,
    }


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "LeafAntenna/1.0"

    def log_message(self, *args):  # keep the console quiet
        pass

    # --- helpers ---
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _serve_file(self, path, ctype):
        try:
            with open(path, "rb") as fh:
                self._send(200, fh.read(), ctype)
        except FileNotFoundError:
            self._send(404, {"error": f"not found: {os.path.basename(path)}"})

    # --- routes ---
    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route in ("/", "/index.html"):
            return self._serve_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")
        if route == "/api/config":
            return self._send(200, _config())
        if route.startswith("/web/"):
            fname = os.path.basename(route)
            ctype = "text/css" if fname.endswith(".css") else "application/javascript"
            return self._serve_file(os.path.join(WEB_DIR, fname), ctype)
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        route = self.path.split("?", 1)[0]
        body = self._read_json()
        try:
            if route == "/api/simulate":
                return self._send(200, _sim_payload(body.get("params", {})))

            if route == "/api/chat":
                res = chatbot.interpret(body.get("message", ""), clip_all(body.get("params", {})))
                return self._send(200, res)

            if route == "/api/geometry":
                return self._send(200, {"png": _geometry_png(body.get("params", {}))})

            if route == "/api/vba":
                return self._send(200, {"vba": generate_vba(clip_all(body.get("params", {})))})

            if route == "/api/optimize":
                budget = int(body.get("budget", 300))
                # Safety: in live CST mode each eval is a ~2-min solve, so hard-cap
                # the budget to avoid multi-hour runs even if the client asks for more.
                if not cst_link.DEMO_MODE:
                    budget = min(budget, 40)
                best = optimizer.optimize(
                    run_simulation,
                    clip_all(body.get("params", {})),
                    include_all=bool(body.get("include_all", True)),
                    budget=budget,
                )
                return self._send(200, {
                    "params": best["params"],
                    "analysis": best["analysis"],
                    "gain": None if best["gain"] is None else round(float(best["gain"]), 3),
                    "freqs": np.asarray(best["freqs"], dtype=float).round(5).tolist(),
                    "s11_db": np.asarray(best["s11_db"], dtype=float).round(4).tolist(),
                    "score": round(float(best["score"]), 3),
                    "evals": int(best["evals"]),
                })

            return self._send(404, {"error": "unknown endpoint"})
        except Exception as exc:  # never 500 with a stack trace; report cleanly
            return self._send(200, {"error": str(exc)})


def main():
    ap = argparse.ArgumentParser(description="Leaf Antenna Interface (local web server)")
    ap.add_argument("--port", type=int, default=8501)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://localhost:{args.port}"
    mode = "DEMO" if cst_link.DEMO_MODE else "LIVE CST"
    print(f"Leaf Antenna Interface [{mode}] -> {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
