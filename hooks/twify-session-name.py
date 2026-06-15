#!/usr/bin/env python3
"""Force auto-generated session names (ai-title) to Traditional Chinese (zh-TW).

Claude Code auto-names sessions via a background Haiku call and writes the name
into the session transcript as lines like:
    {"type":"ai-title","aiTitle":"...","sessionId":"..."}
All UI surfaces (status line, Ctrl+R picker, terminal title) read the LATEST
such line. Claude Code offers no setting to control the language, so this hook
reads the latest ai-title, converts it with OpenCC (s2twp = Simplified ->
Traditional, Taiwan standard + phrases), and appends a corrected line when it
differs. Self-healing: it re-runs each turn, so any newly regenerated
Simplified title gets converted on the next turn.

Fails open: any error exits 0 so Claude Code is never blocked.
"""
import sys
import json
import io


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    transcript_path = data.get("transcript_path")
    if not transcript_path:
        return 0

    try:
        with io.open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return 0

    # Find the latest ai-title entry.
    last_title = None
    last_session_id = data.get("session_id", "")
    for line in reversed(lines):
        line = line.strip()
        if not line or '"ai-title"' not in line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") == "ai-title" and obj.get("aiTitle"):
            last_title = obj.get("aiTitle")
            last_session_id = obj.get("sessionId") or last_session_id
            break

    if not last_title:
        return 0

    # Convert Simplified -> Traditional (Taiwan).
    try:
        from opencc import OpenCC
        converted = OpenCC("s2twp").convert(last_title)
    except Exception:
        return 0

    if converted == last_title:
        return 0  # already Traditional / no change -> idempotent, no growth

    entry = {
        "type": "ai-title",
        "aiTitle": converted,
        "sessionId": last_session_id,
    }
    try:
        with io.open(transcript_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
