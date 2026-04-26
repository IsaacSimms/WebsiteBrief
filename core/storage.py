# == storage.py == #
# Writes pipeline outputs to disk and cleans up old files.
#
# Output locations:
#   outputs/briefs/brief_YYYYMMDD_HHMMSS.md       — the generated Markdown brief
#   outputs/conversations/conversation_YYYYMMDD_HHMMSS.json — full prompt + response
#   outputs/logs/websitebrief.log                 — rotating log (written by run.py)
#
# Cleanup: every time save_brief() runs it deletes .md files in briefs/ that are
# older than brief_retention_days (default 30). This keeps the folder tidy on
# scheduled weekly runs without any manual housekeeping.

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

# Module-level path constants.
# tests/test_storage.py swaps these out via monkeypatch so tests never
# touch the real outputs/ directory.
BRIEFS_DIR        = Path("outputs") / "briefs"
CONVERSATIONS_DIR = Path("outputs") / "conversations"
LOGS_DIR          = Path("outputs") / "logs"


def _ensure_dirs() -> None:
    for directory in (BRIEFS_DIR, CONVERSATIONS_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    # UTC timestamp formatted for safe use in filenames (no colons or spaces).
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def cleanup_old_files(directory: Path, extension: str, days: int = 30) -> int:
    # == cleanup_old_files == #
    # Delete files matching `extension` in `directory` whose last-modified time
    # is older than `days` days. Returns the number of files deleted.
    #
    # Uses the file system's mtime (modification time) rather than parsing
    # the filename timestamp, so it works for any file naming convention.

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = 0

    for f in directory.glob(f"*{extension}"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            f.unlink()
            log.info("Deleted old file: %s", f.name)
            deleted += 1

    return deleted


def save_brief(brief_text: str, retention_days: int = 30) -> Path:
    # == save_brief == #
    # Write the generated Markdown brief to disk, then clean up old briefs.
    # Returns the Path of the newly written file.

    _ensure_dirs()
    cleanup_old_files(BRIEFS_DIR, ".md", days=retention_days)

    path = BRIEFS_DIR / f"brief_{_timestamp()}.md"
    path.write_text(brief_text, encoding="utf-8")
    log.info("Brief saved: %s", path)
    return path


def save_conversation(prompt: str, response: str) -> Path:
    # == save_conversation == #
    # Write the full prompt and response to a JSON file for debugging.
    # Useful for inspecting exactly what was sent to the AI without re-running
    # the scraper, and for verifying prompt caching is working.

    _ensure_dirs()
    path = CONVERSATIONS_DIR / f"conversation_{_timestamp()}.json"
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
        "response": response,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Conversation saved: %s", path)
    return path
