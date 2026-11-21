# Context Engineering track

Part of the Advanced Agentic AI program. Over eight weeks you build **NovaAssist**, a support agent for the
fictional company NovaTech, and learn to decide what a model sees and to prove it with traces and measurements.

## Folders

| Folder | What it is | Who changes it |
|---|---|---|
| `work/` | **Your workspace.** Your NovaAssist code, Context Spec, labs, traces. Your own Git repository. | You |
| `checkpoints/` | Each session's starting state, released before the session | The course team (you get it with `git pull`) |
| `tools/`, `ce.py`, `pyproject.toml`, `uv.lock` | Course helper and the pinned Python environment | The course team |
| `models/`, `backups/`, `.venv/` | Downloaded models, automatic backups, the environment | Created on your laptop; never committed |

`work/` is not part of this repository, so `git pull` never touches your code.

## First-time setup (once)

Windows (PowerShell):

    mkdir C:\ce ; cd C:\ce
    git clone <course repository URL> ce-track
    cd ce-track
    uv sync
    uv run ce.py setup

Mac (Terminal):

    mkdir -p ~/ce && cd ~/ce
    git clone <course repository URL> ce-track
    cd ce-track
    uv sync
    uv run ce.py setup

`uv sync` takes 5 to 20 minutes and about 1.5 GB the first time. Keep the folder at exactly this location:
deeper folders and OneDrive folders break the install on Windows.
Setup ends with a readiness summary. **READY** means you are set for the first sessions.

## Before every session

    cd C:\ce\ce-track          (Mac: cd ~/ce/ce-track)
    git pull
    uv sync
    uv run ce.py update

`update` adds the new session's lab folder and refreshes the kit folders. It never changes your own code.

## Working on a lab

    cd work
    uv run python labs/m1/run_probes.py --spec context_spec/example_spec.yaml

Always start commands with `uv run`, so they use the course environment. Each lab's `README.md` has its steps.
In VS Code, open the `work` folder and pick the `.venv` interpreter of the course folder for notebooks.

## Save your work to your GitHub

`work/` is already a Git repository. Commit after each session, and push it to a **private** repository on your
own GitHub account:

    cd work
    git add -A
    git commit -m "Session 1 lab"

## Your API key

Until your personal course key arrives, the kit runs with an offline stand-in model (`LLM_PROVIDER=fake`).
When it arrives, open `work/.env`, set `LLM_PROVIDER=openai` and paste the key after `LLM_API_KEY=`.
Never commit, post or share the key. It has a spending cap; ask the mentors if you hit it.

## If something goes wrong

| Problem | Fix |
|---|---|
| `uv` not found | Install uv (setup guide), then open a new terminal |
| Install fails with "No such file or directory" on Windows | The folder path is too long: clone again into `C:\ce\ce-track` |
| Lab files broken beyond repair | `uv run ce.py reset S01` restores a session's starting state; your files go to `backups/` first |
| Anything else | `uv run ce.py check`, then post a screenshot of the summary in the Classroom help thread |
