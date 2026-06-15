#!/usr/bin/env python3
"""Objective low-level comprehension test for C1.

Instead of asking the model whether it understood (models are bad witnesses, even
to themselves), ask it concrete questions. Pass means it can extract the load-
bearing points from the thread.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
THREAD_PATH = ROOT / "outputs" / "C1-human-readable-thread.md"
OUT_MD = ROOT / "outputs" / "C1-objective-comprehension-check.md"
OUT_JSON = ROOT / "outputs" / "C1-objective-comprehension-check.json"
MODELS = ["llama3.2:latest", "llama3.1:8b"]
EXPECTED = {
    "q1": "B",  # not zero wealth
    "q2": "B",  # sale can push price down
    "q3": "B",  # headline is not settled cash
    "q4": "B",  # still raises a lot, less than headline
}


def extract_thread(text: str) -> str:
    m = re.search(r"## Thread\n\n(.*?)\n\n## Human-readable intent", text, re.S)
    if not m:
        raise SystemExit("Could not extract thread section")
    return m.group(1).strip()


def call_ollama(model: str, prompt: str) -> dict:
    payload = json.dumps({
        "model": model,
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
    with urllib.request.urlopen(req, timeout=240) as resp:
        raw = json.loads(resp.read().decode("utf-8"))["response"]
    try:
        return json.loads(raw)
    except Exception:
        try:
            start, end = raw.index("{"), raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except Exception:
            return {"parse_error": True, "raw": raw}


def main() -> int:
    thread = extract_thread(THREAD_PATH.read_text(encoding="utf-8"))
    prompt = f"""
Read this Twitter/X thread, then answer four multiple-choice comprehension questions.
Do not judge whether the thread is correct. Only answer what it says.

THREAD:
{thread}

Questions:
q1. Does the thread claim billionaires have zero real wealth?
A. Yes, it says there is no real wealth.
B. No, it says there is real wealth, but the headline number is not cash.
C. It does not discuss this.

q2. According to the thread, what can happen when a huge block of stock is sold?
A. The price must stay the same.
B. The selling itself can push the price down.
C. The price always goes up.

q3. What is the main category mistake the thread warns against?
A. Treating cash as stock.
B. Treating a current market estimate as cash you can collect by selling everything.
C. Treating taxes as redistribution.

q4. What strongest objection does the thread concede?
A. Billionaires usually hold only cash.
B. Selling would still raise a lot of money, just likely less than the headline value.
C. Stock prices never change during large sales.

Return ONLY valid JSON:
{{
  "q1": "A/B/C",
  "q2": "A/B/C",
  "q3": "A/B/C",
  "q4": "A/B/C",
  "one_sentence_summary": "...",
  "confusing_phrases": ["..."]
}}
""".strip()
    results = []
    for model in MODELS:
        parsed = call_ollama(model, prompt)
        correct = {k: parsed.get(k) == v for k, v in EXPECTED.items()}
        score = sum(correct.values())
        results.append({"model": model, "answers": parsed, "correct": correct, "score": score, "passed": score >= 4})
    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# C1 Objective Comprehension Check", "", "Expected pass: 4/4 on load-bearing questions.", ""]
    for r in results:
        lines.append(f"## {r['model']}")
        lines.append("")
        lines.append(f"Score: {r['score']}/4")
        lines.append(f"Passed: {r['passed']}")
        lines.append("")
        lines.append("Answers:")
        lines.append("```json")
        lines.append(json.dumps(r["answers"], indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
