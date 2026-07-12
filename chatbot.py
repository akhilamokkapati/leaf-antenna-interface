"""
chatbot.py - natural language -> parameter changes.

Public entry point:

    interpret(message, current_params) -> {"changes": {param: value, ...},
                                           "reply": "<one sentence>"}

If ANTHROPIC_API_KEY is set we ask Claude to translate the message into JSON
parameter edits. On ANY error (no key, no network, bad JSON, unknown model) we
fall back to a deterministic rule parser so the demo always works offline.

All resulting values are clipped to their ranges via cst_link.clip_param.
"""

from __future__ import annotations

import json
import os
import re

from cst_link import PARAM_SPEC, PARAM_ORDER, clip_param, defaults

# Chat model. The project prompt asked for "claude-sonnet-4-6"; it's a single
# configurable constant. Current valid alternatives include "claude-sonnet-5"
# and "claude-opus-4-8" - change this one line to switch models.
CHAT_MODEL = "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def interpret(message: str, current_params: dict) -> dict:
    """Turn a user message into {changes, reply}. Never raises."""
    message = (message or "").strip()
    if not message:
        return {"changes": {}, "reply": "Tell me what to change, e.g. 'add 2 fins'."}

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return _interpret_with_claude(message, current_params)
        except Exception:
            # Any failure -> silently fall back to the rule parser.
            pass
    return _interpret_with_rules(message, current_params)


# ---------------------------------------------------------------------------
# Claude-backed interpretation
# ---------------------------------------------------------------------------
def _system_prompt() -> str:
    lines = [
        "You translate a user's plain-English request into parameter edits for a",
        "2.45 GHz biomimetic 'leaf' WiFi antenna designed in CST.",
        "",
        "Tunable parameters (name: range, default - effect):",
    ]
    for k in PARAM_ORDER:
        lo, hi, dflt, _step, unit, eff = PARAM_SPEC[k]
        u = f" {unit}" if unit else ""
        lines.append(f"- {k}: {lo}-{hi}{u}, default {dflt} - {eff}")
    lines += [
        "",
        "Physics: longer leaf_length -> lower resonance; more num_fin_pairs -> lower",
        "resonance AND deeper match; wider fin_width -> deeper match; larger",
        "leaf_ground_gap -> detune/shallower match; rim_width best near 4.2.",
        "",
        "Reply with ONLY a JSON object, no prose, no code fences:",
        '{"changes": {"<param>": <number>, ...}, "reply": "<one short sentence>"}',
        "Only include parameters you are changing. Numbers must be within range.",
        "If the user only asks a question, return empty changes and answer in reply.",
    ]
    return "\n".join(lines)


def _interpret_with_claude(message: str, current_params: dict) -> dict:
    import anthropic  # imported lazily so the app runs without the package

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    user_block = (
        f"Current parameters: {json.dumps(current_params)}\n"
        f"User request: {message}"
    )
    resp = client.messages.create(
        model=CHAT_MODEL,
        max_tokens=400,
        system=_system_prompt(),
        messages=[{"role": "user", "content": user_block}],
    )
    text = "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    )
    data = _parse_json_reply(text)
    changes = {}
    for k, v in (data.get("changes") or {}).items():
        if k in PARAM_SPEC:
            changes[k] = clip_param(k, v)
    reply = str(data.get("reply") or "Updated the parameters.")
    return {"changes": changes, "reply": reply}


def _parse_json_reply(text: str) -> dict:
    """Strip code fences and parse the first JSON object in the text."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # Grab the outermost {...} in case the model added stray words.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


# ---------------------------------------------------------------------------
# Rule-parser fallback (fully offline, deterministic)
# ---------------------------------------------------------------------------
# Map friendly words a user might type to canonical parameter names.
_ALIASES = {
    "fins": "num_fin_pairs",
    "fin pairs": "num_fin_pairs",
    "fin_pairs": "num_fin_pairs",
    "num fin pairs": "num_fin_pairs",
    "num_fin_pairs": "num_fin_pairs",
    "leaf length": "leaf_length",
    "leaf_length": "leaf_length",
    "length": "leaf_length",
    "rim width": "rim_width",
    "rim_width": "rim_width",
    "rim": "rim_width",
    "stem width": "center_stem_width",
    "center stem width": "center_stem_width",
    "center_stem_width": "center_stem_width",
    "stem": "center_stem_width",
    "fin width": "fin_width",
    "fin_width": "fin_width",
    "ground gap": "leaf_ground_gap",
    "leaf ground gap": "leaf_ground_gap",
    "leaf_ground_gap": "leaf_ground_gap",
    "gap": "leaf_ground_gap",
}


def _num(text: str):
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


def _knowledge(msg: str) -> dict:
    """Answer common concept questions (offline). Returns {changes:{}, reply}."""
    def r(t):
        return {"changes": {}, "reply": t}
    if "s11" in msg or "s-11" in msg or "return loss" in msg or "reflect" in msg:
        return r("S11 (return loss) is how much power bounces back instead of radiating. "
                 "More negative is better - below -10 dB means over 90% of the power is accepted.")
    if "resonan" in msg or "resonate" in msg:
        return r("Resonance is the frequency where the antenna works best - the deepest dip in "
                 "the S11 curve. We tune it to 2.45 GHz (the WiFi band).")
    if "bandwidth" in msg:
        return r("Bandwidth is the span of frequencies where S11 stays below -10 dB. Wider = the "
                 "antenna tolerates more detuning.")
    if "impedance" in msg or "matching" in msg or "50 ohm" in msg or "50ohm" in msg:
        return r("Impedance matching makes the antenna look like 50 ohm to the feed, so power "
                 "transfers with minimal reflection. A perfect match is 50 + j0 ohm.")
    if "efficiency" in msg or "gain" in msg or "directiv" in msg:
        return r("Total efficiency is the fraction of input power actually radiated (it includes "
                 "the impedance match) - higher is better. Real gain/directivity needs farfield "
                 "post-processing, so this tool reports efficiency instead.")
    if "water" in msg or "flood" in msg or "sensing" in msg or "permittivity" in msg:
        return r("As water rises into the antenna's near field, the effective permittivity goes up "
                 "and the resonance shifts down. Tracking that shift is how it senses water level "
                 "(contactless flood monitoring) - try the water-level slider under the S11 plot.")
    if "fin" in msg or "vein" in msg:
        return r("The fins (leaf veins) are shunt stubs along the central stem. They add capacitance "
                 "that lowers the resonance and deepens the impedance match. The macro clamps at 8.")
    if "leaf length" in msg or "leaf_length" in msg or ("leaf" in msg and "length" in msg) or "length" in msg:
        return r("leaf_length is the primary frequency knob: a longer leaf lowers the resonant "
                 "frequency, a shorter leaf raises it.")
    if "rim" in msg:
        return r("rim_width is the outer leaf trace width; it mainly affects the impedance match "
                 "(best near 4.2 mm).")
    if "ground" in msg or "gap" in msg:
        return r("leaf_ground_gap is the gap to the ground plane. A smaller gap increases capacitive "
                 "coupling and improves the match (adjustable down to 0.1 mm).")
    if "stem" in msg:
        return r("center_stem_width is the feed-stem width - it has a small effect on frequency and "
                 "the match.")
    if "antenna" in msg:
        return r("An antenna converts electrical signals into radio waves and back. This is a "
                 "2.45 GHz leaf-shaped WiFi antenna - the leaf rim and internal 'fin' veins tune "
                 "where it resonates.")
    if any(k in msg for k in ("how", "work", "use", "do i", "help")):
        return r("Tune the 2.45 GHz leaf antenna with the sliders or by asking me (e.g. 'add 2 fins', "
                 "'set leaf length to 80', 'make it resonate lower', 'deeper match'), then press Run "
                 "to simulate S11 in CST. I can also explain terms like S11, resonance, impedance.")
    return r("I can tune the antenna ('add 2 fins', 'set leaf length to 80', 'resonate lower', "
             "'deeper match', 'reset') and explain terms like S11, resonance, impedance, bandwidth, "
             "fins. What would you like?")


def _interpret_with_rules(message: str, current_params: dict) -> dict:
    msg = message.lower().strip()
    params = dict(current_params)

    # 1) reset / defaults
    if re.search(r"\b(reset|default|defaults|start over)\b", msg):
        return {
            "changes": defaults(),
            "reply": "Reset all six parameters to their defaults.",
        }

    # 2) concept questions (interrogative start) -> answer, don't tune.
    #    Guarded to interrogative openers so imperatives like "make it resonate
    #    lower?" still tune, while "why more fins" / "what is S11" get answered.
    if re.match(r"^(why|what|whats|what'?s|which|explain|define|how|tell me|is |are |does )", msg):
        return _knowledge(msg)

    # 3) relative fin changes - MUST run before numeric direct-set so
    #    "add 2 fins" isn't misread as num_fin_pairs = 2.
    if "fin" in msg and re.search(r"\b(add|more|increase|remove|fewer|less|reduce|decrease)\b", msg):
        cur = current_params["num_fin_pairs"]
        n = _num(msg)
        delta = int(n) if n is not None else 1
        if re.search(r"\b(remove|fewer|less|reduce|decrease)\b", msg):
            delta = -delta
        new = clip_param("num_fin_pairs", cur + delta)
        if new == cur:  # already clamped at the min (3) or max (8)
            edge = "maximum of 8" if delta > 0 else "minimum of 3"
            way = "higher" if delta > 0 else "lower"
            return {"changes": {},
                    "reply": f"Already at the {edge} fin pairs - can't go {way} (the macro clamps at 8)."}
        return {"changes": {"num_fin_pairs": new},
                "reply": f"Changed fin pairs from {cur} to {new}. Press Run to simulate."}

    # 4) match intent - "deeper/better match" -> fin_width +0.3
    if "match" in msg and re.search(r"\b(deep|deeper|better|improve|stronger)\b", msg):
        cur = current_params["fin_width"]
        new = clip_param("fin_width", cur + 0.3)
        return {"changes": {"fin_width": new},
                "reply": f"Widened fins to {new} mm for a deeper match. Press Run."}
    if "match" in msg and re.search(r"\b(shallow|weaker|worse)\b", msg):
        cur = current_params["fin_width"]
        new = clip_param("fin_width", cur - 0.3)
        return {"changes": {"fin_width": new},
                "reply": f"Narrowed fins to {new} mm. Press Run."}

    # 5) frequency intent - "resonate lower/higher" -> leaf_length -/+ 3
    if re.search(r"\b(resonat|frequency|freq|tune)\w*", msg) or "resonance" in msg:
        cur = current_params["leaf_length"]
        if re.search(r"\b(lower|down|decrease|reduce)\b", msg):
            new = clip_param("leaf_length", cur + 3.0)  # longer leaf -> lower freq
            return {"changes": {"leaf_length": new},
                    "reply": f"Lengthened the leaf to {new} mm to resonate lower. Press Run."}
        if re.search(r"\b(higher|up|increase|raise)\b", msg):
            new = clip_param("leaf_length", cur - 3.0)  # shorter leaf -> higher freq
            return {"changes": {"leaf_length": new},
                    "reply": f"Shortened the leaf to {new} mm to resonate higher. Press Run."}

    # 6) direct set - "set leaf length to 80", "fins = 6", "gap 8"
    for phrase, canonical in sorted(_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if phrase in msg:
            n = _num(msg)
            if n is not None:
                new = clip_param(canonical, n)
                return {"changes": {canonical: new},
                        "reply": f"Set {canonical} to {new}. Press Run to simulate."}

    # 7) not a tuning command -> answer as a concept question / helpful hint
    return _knowledge(msg)
