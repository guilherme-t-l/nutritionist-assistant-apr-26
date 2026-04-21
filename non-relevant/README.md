# Files and folders you can ignore (for learning purposes)

Everything **worth reading while you learn** lives under `src/`, `tests/`,
and (in later phases) `agent/`, `tools/`, `evals/`, plus the root
`README.md` and `pyproject.toml`.

This folder is a **junk drawer**: real noise lives here, and **shortcuts**
(symlinks) point at a few things that *must* stay at the project root
because `uv` / Python / git hardcode those paths. Open the shortcuts if
you ever need to peek; day to day, collapse this folder in the sidebar and
forget it.

---

## What actually lives inside `non-relevant/`

| Name | What it is |
|------|------------|
| `.pytest_cache/` | Pytest’s cache (real directory). Location set by `cache_dir` in `pyproject.toml`. |
| `uv.lock` | **Symlink** → `../uv.lock`. The real file stays at the repo root; `uv` requires it there. |
| `.python-version` | **Symlink** → `../.python-version`. Same story — `uv` reads the root file. |
| `virtual-environment` | **Symlink** → `../.venv`. Your installed packages; the real folder stays at root. |

**Why symlinks instead of moving the files?**  
If we moved `uv.lock` or `.venv` into this folder, `uv sync` and imports
would break. Symlinks give you “one place to look” without fighting the
tools.

**Windows note:** Git can store symlinks, but cloning on Windows sometimes
turns them into plain text files unless `core.symlinks` is enabled. If
that happens, delete the broken entries and re-run:

```bash
cd non-relevant
ln -sf ../uv.lock uv.lock
ln -sf ../.python-version .python-version
ln -sf ../.venv virtual-environment
```

(or recreate them however your OS prefers).

---

## Things that still live only at the project root (no symlink)

These are listed so you know not to hunt for them under `non-relevant/`.

### `.git/` (project root)

The entire git repository — history, branches, hooks.

- **You edit this folder:** never directly; use `git` commands.
- **Safe to delete:** only if you want to throw away all history.

### `__pycache__/` (next to `.py` files under `src/`, `tests/`, …)

Compiled bytecode. Python writes it next to your source; there is no
supported “relocate all caches here” switch without trade-offs.

- **Safe to delete:** yes; Python recreates on import.

### `.env` (project root)

Secrets (e.g. `GEMINI_API_KEY`). Gitignored.

- **You edit this file:** when you paste a real API key (Phase 1+).

### `.gitignore` (project root)

Patterns git should skip. Worth reading once.

### `.cursor/` (project root)

Cursor rules for the AI. Not part of the app runtime.

---

## Auto-generated elsewhere (for context)

### `uv.lock` (real file at project root)

Exact resolved versions of every dependency. Updated by `uv add` /
`uv lock` / `uv sync`. Analogue: `package-lock.json`.

- **You edit this file:** never.

### `.venv/` (real folder at project root)

Isolated Python + installed libraries from `pyproject.toml`.

- **You edit this folder:** never.
- **Safe to delete:** yes; run `uv sync` to recreate.

### `.python-version` (real file at project root)

One line, pins the Python version for this project.

---

## Rule of thumb

If you didn’t write it and it doesn’t end in `.py`, `.md`, `.toml`,
`.html`, `.json`, or `.env` (or live under `src/` / `tests/` / `agent/` /
`tools/` / `evals/` / `frontend/`), treat it as tooling noise — skim this
README once, then focus on `src/` and `tests/`.
