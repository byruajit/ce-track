"""Course helper for the Context Engineering track. Run every command from the course folder.

    uv run ce.py setup          first time: create work/, write work/.env, download the two models, run the check
    uv run ce.py check          readiness check (prints what you need now and what can wait)
    uv run ce.py update         after `git pull`: add new lab folders and refresh kit folders; your code is untouched
    uv run ce.py reset S01      put work/ back to a session's starting state (asks first; your files are backed up)
    uv run ce.py list           sessions released so far

You write your code in work/. Git never touches work/ when you pull, so your work and course updates never collide.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Readiness-check names (from work/scripts/preflight.py) that are not needed in the first sessions,
# with the local fix to show instead of the hosted-course wording.
LATER = {
    "tesseract OCR": "needed from Module 2; installation steps come with that session",
    "LLM call": "needs your personal course API key in work/.env (sent to you privately); until then LLM_PROVIDER=fake works",
    "api.openai.com reachable": "needed once you have your API key; check your internet connection or proxy",
    "shared Neo4j": "needed in Module 10 only",
}
FIXES = {
    "python version": "run commands with `uv run ...` from the course folder, not with a plain `python`",
    "packages importable": "run `uv sync` in the course folder, then try again",
    "embedding model": "run `uv run ce.py setup` again while online (the models download once)",
    "reranker model": "run `uv run ce.py setup` again while online (the models download once)",
    "git": "install Git (see the setup guide) and open a new terminal",
}
WORK_GITIGNORE = """\
.env
__pycache__/
*.pyc
.ipynb_checkpoints/
indexes/
*.faiss
*.index
qdrant_data/
submissions/
preflight_report.txt
"""


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {"work": root / "work", "checkpoints": root / "checkpoints", "backups": root / "backups",
            "models": root / "models"}


def load_reset(root: Path = ROOT):
    """The course's checkpoint restore logic (tools/ce_reset.py, shipped with each release)."""
    spec = importlib.util.spec_from_file_location("ce_reset", root / "tools" / "ce_reset.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def released(root: Path = ROOT) -> list[str]:
    return load_reset(root).available(paths(root)["checkpoints"])


def latest(root: Path = ROOT) -> str:
    sessions = released(root)
    if not sessions:
        sys.exit("No sessions released yet. Run `git pull` and try again.")
    return sessions[-1]


def child_env(root: Path = ROOT) -> dict[str, str]:
    env = dict(os.environ)
    env.update({"PYTHONIOENCODING": "utf-8", "HF_HUB_DISABLE_SYMLINKS_WARNING": "1",
                "MODEL_CACHE_DIR": str(paths(root)["models"])})
    return env


def env_file_text(example: str, models: Path) -> str:
    """work/.env for a laptop: every setting of .env.example, with the local values below."""
    overrides = {"LLM_PROVIDER": "fake", "HF_HOME": "", "HF_HUB_OFFLINE": "1", "MODEL_CACHE_DIR": str(models)}
    lines = ["# Your local settings. Never commit, upload or share this file.",
             "# When your course API key arrives: set LLM_PROVIDER=openai and paste the key after LLM_API_KEY=", ""]
    for line in example.splitlines():
        match = re.match(r"\s*([A-Z][A-Z0-9_]*)=([^#]*)", line)
        if match:
            key = match.group(1)
            lines.append(f"{key}={overrides.get(key, match.group(2).strip())}")
    return "\n".join(lines) + "\n"


def restore(session: str, kit_only: bool, root: Path = ROOT, dry_run: bool = False) -> dict:
    p = paths(root)
    return load_reset(root).reset(session, p["work"], p["checkpoints"], kit_only=kit_only, dry_run=dry_run,
                                  backup_root=p["backups"])


def create_work(root: Path = ROOT) -> bool:
    """Create work/ from the latest release; False if it already exists."""
    p = paths(root)
    if (p["work"] / ".ce-l2-state.json").exists():
        return False
    session = latest(root)
    restore(session, kit_only=False, root=root)
    env = p["work"] / ".env"
    if not env.exists():
        env.write_text(env_file_text((p["work"] / ".env.example").read_text(encoding="utf-8"), p["models"]),
                       encoding="utf-8")
    gitignore = p["work"] / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(WORK_GITIGNORE, encoding="utf-8")
    print(f"created {p['work']} from {session}")
    return True


def init_git(work: Path) -> None:
    """Make work/ your own Git repository (push it to your GitHub later)."""
    if (work / ".git").exists():
        return
    try:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=work, check=True)
        subprocess.run(["git", "add", "-A"], cwd=work, check=True)
        done = subprocess.run(["git", "commit", "-q", "-m", "Starting point"], cwd=work)
    except (OSError, subprocess.CalledProcessError):
        print("note: Git is not working yet; work/ is not a Git repository (see the setup guide)")
        return
    if done.returncode != 0:
        print('note: first commit failed. Run once:  git config --global user.name "Your Name"  and\n'
              '      git config --global user.email "you@example.com", then in work/:  git commit -m "Starting point"')


def download_models(root: Path = ROOT) -> int:
    work = paths(root)["work"]
    env = child_env(root) | {"HF_HUB_OFFLINE": "0"}
    print("downloading the embedding and reranker models (about 130 MB, once) ...")
    return subprocess.run([sys.executable, "scripts/download_models.py", "--download"], cwd=work, env=env).returncode


def summarise(report: str) -> tuple[list[str], list[str]]:
    """(blocking failures, failures that can wait) from a preflight report."""
    blocking, later = [], []
    for name in re.findall(r"^\[FAIL\] ([^:]+):", report, flags=re.M):
        (later if name in LATER else blocking).append(name)
    return blocking, later


def check(root: Path = ROOT) -> int:
    work = paths(root)["work"]
    if not (work / "scripts" / "preflight.py").exists():
        print("work/ does not exist yet: run `uv run ce.py setup` first")
        return 1
    report_path = work / "preflight_report.txt"
    subprocess.run([sys.executable, "scripts/preflight.py", "--report", str(report_path)], cwd=work,
                   env=child_env(root))
    blocking, later = summarise(report_path.read_text(encoding="utf-8"))
    print("\n" + "=" * 60)
    for name in later:
        print(f"can wait   {name}: {LATER[name]}")
    for name in blocking:
        print(f"FIX NOW    {name}: {FIXES.get(name, 'post the report in the Classroom help thread')}")
    print("READY for the first sessions" if not blocking else "NOT READY: fix the items marked FIX NOW")
    print(f"report: {report_path}  (post a screenshot of this summary in Classroom)")
    return 1 if blocking else 0


def warn_location(root: Path = ROOT) -> None:
    text = str(root)
    if "onedrive" in text.lower():
        print("WARNING: the course folder is inside OneDrive. Move it to C:\\ce (Windows) or ~/ce (Mac); "
              "OneDrive syncing breaks Python environments.")
    elif sys.platform == "win32" and len(text) > 40:
        print(f"WARNING: the course folder path is long ({len(text)} characters). If installs fail, "
              "clone the course again into C:\\ce\\ce-track.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Context Engineering track helper")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="first-time setup")
    sub.add_parser("check", help="readiness check")
    sub.add_parser("update", help="bring in new labs and kit updates after git pull")
    reset = sub.add_parser("reset", help="restore work/ to a session's starting state")
    reset.add_argument("session", help="e.g. S01")
    reset.add_argument("--yes", action="store_true", help="do it without asking")
    sub.add_parser("list", help="sessions released so far")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(line_buffering=True)  # keep our lines in order with the child scripts' output

    if args.command == "list":
        print("released:", ", ".join(released()))
        return 0
    if args.command == "setup":
        warn_location()
        if not create_work():
            print("work/ already exists (use `uv run ce.py update` after a git pull)")
        init_git(paths()["work"])
        if download_models() != 0:
            print("model download failed: check your internet connection and run `uv run ce.py setup` again")
            return 1
        return check()
    if args.command == "check":
        return check()
    if args.command == "update":
        if not (paths()["work"] / ".ce-l2-state.json").exists():
            print("work/ does not exist yet: run `uv run ce.py setup` first")
            return 1
        session = latest()
        result = restore(session, kit_only=True)
        for rel, action in result["actions"]:
            print(f"  {action:<7} {rel}")
        print(f"work/ is up to date with {session}; your code was not changed")
        return 0
    if args.command == "reset":
        session = args.session.upper()
        if session not in released():
            print(f"{session} is not released (released: {', '.join(released())})")
            return 1
        preview = restore(session, kit_only=False, dry_run=True)
        print(f"This replaces these folders in work/ with the {session} starting state:")
        for rel, _ in preview["actions"]:
            print(f"  {rel}")
        print("Your current files are copied to backups/ first. Your .env and .git are never touched.")
        if not args.yes and input("Type yes to continue: ").strip().lower() != "yes":
            print("nothing changed")
            return 1
        result = restore(session, kit_only=False)
        print(f"work/ restored to {session}; previous files in {result['backup']}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
