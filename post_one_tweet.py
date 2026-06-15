#!/usr/bin/env python3
"""Post exactly one tweet/reply through xurl marvin-x and verify by reading it back.

Usage:
  python3 post_one_tweet.py --text-file /tmp/tweet.txt [--reply-to TWEET_ID]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

APP = "marvin-x"


def run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=120)
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout, file=sys.stderr)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--reply-to")
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()

    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("empty tweet text")
    if len(text) > 280:
        raise SystemExit(f"tweet too long by raw chars: {len(text)}")

    body: dict[str, object] = {"text": text}
    if args.reply_to:
        body["reply"] = {"in_reply_to_tweet_id": str(args.reply_to)}

    posted = run([
        "xurl", "--app", APP,
        "-X", "POST", "/2/tweets",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(body, ensure_ascii=False),
    ])
    tweet_id = posted.get("data", {}).get("id")
    if not tweet_id:
        raise SystemExit(f"no tweet id in response: {posted}")

    verified = run(["xurl", "--app", APP, "read", str(tweet_id)])
    receipt = {
        "tweet_id": tweet_id,
        "url": f"https://x.com/marvin_panics/status/{tweet_id}",
        "reply_to": args.reply_to,
        "text": text,
        "post_response": posted,
        "verify_response": verified,
    }
    Path(args.receipt).write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"tweet_id": tweet_id, "url": receipt["url"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
