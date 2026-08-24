#!/usr/bin/env python3
"""Codex VS Code transcript scanner.

Reads local Codex session JSONL files and appends user prompts to
.ai-log/session.jsonl. This is a fallback for the VS Code extension path where
repo hooks may not fire directly.
"""
import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

VN_TZ = timezone(timedelta(hours=7))


def git(cmd: str) -> str:
    try:
        return subprocess.check_output(
            cmd.split(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:8]


def codex_sessions_root() -> Path:
    home = os.environ.get("CODEX_HOME")
    if home:
        return Path(home).expanduser() / "sessions"
    return Path.home() / ".codex" / "sessions"


def logged_entry_ids(log_file: Path) -> set[str]:
    ids: set[str] = set()
    if not log_file.exists():
        return ids
    with open(log_file, encoding="utf-8-sig") as f:
        for line in f:
            try:
                entry_id = json.loads(line).get("entry_id")
            except json.JSONDecodeError:
                continue
            if entry_id:
                ids.add(entry_id)
    return ids


def repo_name() -> str:
    origin = git("git remote get-url origin")
    repo = origin.rstrip("/").split("/")[-1] if origin else Path.cwd().name
    return repo[:-4] if repo.endswith(".git") else repo


def iter_session_files(root: Path, hours: int | None):
    if not root.exists():
        return
    cutoff = None
    if hours is not None:
        cutoff = datetime.now().timestamp() - hours * 3600
    for path in root.rglob("*.jsonl"):
        try:
            if cutoff is not None and path.stat().st_mtime < cutoff:
                continue
        except OSError:
            continue
        yield path


def parse_session(path: Path, repo_root: Path):
    session_id = ""
    source = ""
    cwd = ""
    model = ""
    prompts = []

    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = item.get("payload") or {}
                if item.get("type") == "session_meta":
                    session_id = payload.get("session_id") or payload.get("id") or session_id
                    source = payload.get("originator") or payload.get("source") or source
                    cwd = payload.get("cwd") or cwd
                    model = payload.get("model") or model
                    continue
                if item.get("type") != "event_msg" or payload.get("type") != "user_message":
                    continue
                message = (payload.get("message") or "").strip()
                if not message:
                    continue
                client_id = payload.get("client_id") or short_hash(
                    f"{item.get('timestamp','')}:{message}"
                )
                prompts.append((item.get("timestamp") or "", client_id, message))
    except OSError:
        return []

    if source and "codex" not in source.lower() and "vscode" not in source.lower():
        return []

    if cwd:
        try:
            session_cwd = Path(cwd).resolve()
            repo_resolved = repo_root.resolve()
            related = (
                session_cwd == repo_resolved
                or repo_resolved in session_cwd.parents
                or session_cwd in repo_resolved.parents
            )
            if not related:
                return []
        except OSError:
            pass

    entries = []
    for ts_raw, client_id, message in prompts:
        entry_id = f"codex-{session_id or path.stem}-{client_id}"
        entries.append({
            "ts": datetime.now(VN_TZ).isoformat(),
            "tool": "codex",
            "event": "UserPromptSubmit",
            "entry_id": entry_id,
            "session_id": session_id,
            "model": model,
            "repo": repo_name(),
            "branch": git("git rev-parse --abbrev-ref HEAD"),
            "commit": git("git rev-parse --short HEAD"),
            "student": git("git config user.email"),
            "prompt": message[:1000],
            "turn_id": client_id,
            "transcript_path": str(path),
            "source_ts": ts_raw,
            "source": source or "codex_vscode",
        })
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan Codex VS Code logs")
    parser.add_argument("--hours", type=int, default=72)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "session.jsonl"
    seen = logged_entry_ids(log_file)

    entries = []
    for path in iter_session_files(codex_sessions_root(), None if args.all else args.hours):
        for entry in parse_session(path, Path.cwd()):
            if entry["entry_id"] in seen:
                continue
            seen.add(entry["entry_id"])
            entries.append(entry)

    if args.dry_run:
        print(f"[codex-log] DRY RUN would log {len(entries)} prompt(s).")
        return
    if not entries:
        print("[codex-log] No new prompts.")
        return

    with open(log_file, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[codex-log] Logged {len(entries)} prompt(s).")


if __name__ == "__main__":
    main()