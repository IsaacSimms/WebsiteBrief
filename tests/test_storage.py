# == test_storage.py == #
# Tests for core/storage.py.
# Written BEFORE the implementation — this is TDD.
# Run with:  pytest tests/test_storage.py -v

import json
import os
import time
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# We redirect storage to a temp directory so tests don't touch real outputs/.
# The monkeypatch fixture (built into pytest) lets us swap out module-level
# variables for the duration of a test, then restores them automatically.


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """
    Redirect all storage paths to a temporary directory for each test.
    tmp_path is a pytest built-in that gives a fresh empty folder per test.
    autouse=True means every test in this file gets this fixture automatically.
    """
    import core.storage as storage_module
    monkeypatch.setattr(storage_module, "BRIEFS_DIR",        tmp_path / "briefs")
    monkeypatch.setattr(storage_module, "CONVERSATIONS_DIR", tmp_path / "conversations")
    monkeypatch.setattr(storage_module, "LOGS_DIR",          tmp_path / "logs")
    yield tmp_path


# == save_brief Tests == #

class TestSaveBrief:

    def test_creates_file(self, isolated_storage):
        from core.storage import save_brief, BRIEFS_DIR
        path = save_brief("# Weekly Brief\n\nHello world.")
        assert path.exists()

    def test_file_has_md_extension(self, isolated_storage):
        from core.storage import save_brief
        path = save_brief("# Test")
        assert path.suffix == ".md"

    def test_file_content_matches(self, isolated_storage):
        from core.storage import save_brief
        content = "# My Brief\n\n- Item 1\n- Item 2"
        path = save_brief(content)
        assert path.read_text(encoding="utf-8") == content

    def test_file_is_in_briefs_directory(self, isolated_storage):
        from core.storage import save_brief, BRIEFS_DIR
        path = save_brief("content")
        assert path.parent == BRIEFS_DIR

    def test_filename_contains_timestamp(self, isolated_storage):
        from core.storage import save_brief
        path = save_brief("content")
        # Filename format: brief_YYYYMMDD_HHMMSS.md
        assert path.name.startswith("brief_")


# == save_conversation Tests == #

class TestSaveConversation:

    def test_creates_file(self, isolated_storage):
        from core.storage import save_conversation
        path = save_conversation("my prompt", "my response")
        assert path.exists()

    def test_file_has_json_extension(self, isolated_storage):
        from core.storage import save_conversation
        path = save_conversation("p", "r")
        assert path.suffix == ".json"

    def test_file_content_is_valid_json(self, isolated_storage):
        from core.storage import save_conversation
        path = save_conversation("the prompt", "the response")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_json_contains_prompt_and_response(self, isolated_storage):
        from core.storage import save_conversation
        path = save_conversation("the prompt", "the response")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["prompt"] == "the prompt"
        assert data["response"] == "the response"

    def test_json_contains_timestamp(self, isolated_storage):
        from core.storage import save_conversation
        path = save_conversation("p", "r")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "timestamp_utc" in data
        # Should be parseable as an ISO datetime
        datetime.fromisoformat(data["timestamp_utc"])


# == cleanup_old_files Tests == #

class TestCleanupOldFiles:

    def _make_old_file(self, directory: Path, name: str, days_old: int) -> Path:
        """Create a file and backdate its modification time."""
        directory.mkdir(parents=True, exist_ok=True)
        f = directory / name
        f.write_text("content", encoding="utf-8")
        # Set mtime to `days_old` days in the past
        old_time = time.time() - (days_old * 86400)
        os.utime(f, (old_time, old_time))
        return f

    def test_deletes_files_older_than_threshold(self, isolated_storage):
        from core.storage import cleanup_old_files, BRIEFS_DIR
        old_file = self._make_old_file(BRIEFS_DIR, "old.md", days_old=31)
        count = cleanup_old_files(BRIEFS_DIR, ".md", days=30)
        assert count == 1
        assert not old_file.exists()

    def test_keeps_files_within_threshold(self, isolated_storage):
        from core.storage import cleanup_old_files, BRIEFS_DIR
        new_file = self._make_old_file(BRIEFS_DIR, "new.md", days_old=5)
        count = cleanup_old_files(BRIEFS_DIR, ".md", days=30)
        assert count == 0
        assert new_file.exists()

    def test_only_deletes_matching_extension(self, isolated_storage):
        from core.storage import cleanup_old_files, BRIEFS_DIR
        # Create an old .md and an old .txt — only .md should be removed.
        old_md  = self._make_old_file(BRIEFS_DIR, "old.md",  days_old=31)
        old_txt = self._make_old_file(BRIEFS_DIR, "old.txt", days_old=31)
        cleanup_old_files(BRIEFS_DIR, ".md", days=30)
        assert not old_md.exists()
        assert old_txt.exists()

    def test_returns_count_of_deleted_files(self, isolated_storage):
        from core.storage import cleanup_old_files, BRIEFS_DIR
        self._make_old_file(BRIEFS_DIR, "a.md", days_old=40)
        self._make_old_file(BRIEFS_DIR, "b.md", days_old=35)
        self._make_old_file(BRIEFS_DIR, "c.md", days_old=10)   # too recent to delete
        count = cleanup_old_files(BRIEFS_DIR, ".md", days=30)
        assert count == 2

    def test_handles_empty_directory_gracefully(self, isolated_storage):
        from core.storage import cleanup_old_files, BRIEFS_DIR
        BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
        count = cleanup_old_files(BRIEFS_DIR, ".md", days=30)
        assert count == 0

    def test_save_brief_triggers_cleanup(self, isolated_storage):
        from core.storage import save_brief, BRIEFS_DIR
        # Plant an old file before calling save_brief.
        old_file = self._make_old_file(BRIEFS_DIR, "old_brief.md", days_old=31)
        save_brief("new content")
        # save_brief should have cleaned it up.
        assert not old_file.exists()
