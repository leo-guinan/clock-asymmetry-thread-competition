#!/usr/bin/env python3
"""Low-level reader check for a candidate thread using a local Ollama model.

This is not a truth oracle. It is a cheap comprehension canary: if a small local
model cannot restate the point, a tired human on X probably will not do better.
A bleak benchmark, but a useful one.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

MODEL = "llama3.2:latest"
ROOT = Path(__file__).resolve().parent
THREAD_PATH = ROOT / "outputs" / "C1-human-readable-thread.md"
OUT_PATH = ROOT / "outputs" / "C1-low-level-reader-check.md"
JSON_PATH = ROOT / "outputs" / "C1-low-level-reader-check.json"


def extract_thread(text: str) -> str:
    m = re.search(r"## Thread\n\n(.*?)\n\n## Human-readable intent", text, re.S)
    if not m:
        raise SystemExit("Could not extract thread section")
    return m.group(1).strip()


def ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0},
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["response"].strip()


def main() -> int:
    src = THREAD_PATH.read_text(encoding="utf-8")
    thread = extract_thread(src)
    prompt = f"""
You are a low-level reader comprehension tester. You are not judging whether the argument is true. You are checking whether an ordinary smart reader can understand it.

Read this Twitter/X thread:

{thread}

Return ONLY valid JSON with these fields:
- plain_english_summary: one or two sentences
- understood_core_claim: true/false. Mark true if you can accurately restate the main point, even if some phrases are imperfect.
- core_claim_as_you_understand_it: one sentence
- confusing_phrases: list of phrases that may confuse a normal reader
- likely_misreadings: list of likely ways readers will misunderstand it
- readability_score_1_to_10: integer
- publish_safe: true/false
- suggested_fix: one sentence, or an empty string if no fix is needed
""".strip()
    raw = ollama(prompt)
    # Try strict JSON extraction, but preserve raw output if the little beast wanders.
    parsed = None
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        parsed = json.loads(raw[start:end])
    except Exception:
        parsed = {"parse_error": True, "raw": raw}
    JSON_PATH.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# C1 Low-Level Reader Check",
        "",
        f"Model: `{MODEL}`",
        "",
        "## Raw model result",
        "",
        "```json",
        json.dumps(parsed, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Interpretation",
        "",
    ]
    if parsed.get("parse_error"):
        lines.append("The model failed to return parseable JSON. That itself is not a thread failure, just an evaluator failure. Naturally.")
    else:
        lines.append(f"Readability score: {parsed.get('readability_score_1_to_10')}/10")
        lines.append(f"Understood core claim: {parsed.get('understood_core_claim')}")
        lines.append(f"Publish safe according to low-level reader: {parsed.get('publish_safe')}")
        lines.append("")
        lines.append("Core claim as understood:")
        lines.append(str(parsed.get("core_claim_as_you_understand_it")))
        lines.append("")
        lines.append("Suggested fix:")
        lines.append(str(parsed.get("suggested_fix")))
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
