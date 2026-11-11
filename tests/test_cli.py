"""Tests for CLI commands."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subprocess


def _cli_env():
    """Return env dict with isolated temp DB for CLI subprocess tests."""
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='_cli_test.db')}"
    return env


class TestCLIHelp:
    def test_cli_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "satorbit", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_cli_env(),
        )
        assert result.returncode == 0
        assert "sync" in result.stdout
        assert "init" in result.stdout
        assert "status" in result.stdout

    def test_sync_list_groups(self):
        result = subprocess.run(
            [sys.executable, "-m", "satorbit", "sync", "--list-groups"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_cli_env(),
        )
        assert result.returncode == 0
        assert "stations" in result.stdout
        assert "active" in result.stdout


class TestCLIInit:
    def test_init_creates_database(self):
        result = subprocess.run(
            [sys.executable, "-m", "satorbit", "init"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_cli_env(),
        )
        assert result.returncode == 0
        assert "Ground stations" in result.stdout


class TestCLIDemoSync:
    def test_sync_demo(self):
        result = subprocess.run(
            [sys.executable, "-m", "satorbit", "sync", "--demo"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_cli_env(),
        )
        assert result.returncode == 0
        assert "demo" in result.stdout.lower()
