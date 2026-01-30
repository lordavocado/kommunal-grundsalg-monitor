# Repository Guidelines

## Project Structure & Module Organization
`monitor.py` orchestrates Firecrawl discovery, OpenAI classification, and Google Sheets logging, with spreadsheet helpers in `sheets.py`. Municipality metadata and crawl targets live in `sources.json`, while `.env.local` holds API keys (seed from `env.local.example`). Supporting references sit in `docs/` and `diagrams/`, and prototypes or history live in `initial_prd.md` plus `PROJECT_HISTORY.md`. Exploratory scripts belong in `test_crawl4ai.py` alongside any future utilities under `docs/tools/`.

## Build, Test, and Development Commands
Install dependencies with `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`. Run the monitor locally via `python monitor.py`, which expects `env.local` to be loaded by `python-dotenv`. Smoke-test new crawling strategies with `python test_crawl4ai.py`; this script requires crawl4ai (see header instructions). When editing `monitor.py` or `sheets.py`, run `python -m compileall monitor.py sheets.py` to catch syntax regressions before pushing.

## Coding Style & Naming Conventions
Target Python 3.9+ with 4-space indentation, `snake_case` for functions/variables, and `UpperCamelCase` for classes (rare). Keep modules under ~500 lines; factor helpers into `sheets.py` or new modules when logic grows. Prefer explicit lists and type hints (`List[dict]`, `Optional[str]`) as seen in `monitor.py`. Stick to f-strings, early returns for error paths, and descriptive constant names (e.g., `RATE_LIMIT_DELAY`). Run `ruff` or `black` if installed; otherwise mirror the current style.

## Testing Guidelines
There is no CI test suite yet, so rely on targeted scripts. Use `python monitor.py --dry-run` (add a flag if needed) when validating refactors and capture sample logs in `docs/run-notes.md`. For crawling changes, extend `test_crawl4ai.py` with new async tests and follow the `test_*` naming pattern. Keep manual runs under 15 minutes and call out skipped municipalities in the PR description.

## Commit & Pull Request Guidelines
Follow the existing imperative, short (<70 char) subject style (`Add Slack notifications`, `Pin firecrawl version`). Group related code/doc updates in one commit to keep reviewable diffs. PRs should include: summary of behavior changes, verification notes (commands and outputs), linked issue or context, and screenshots/log excerpts for Sheets or Slack impacts. Flag any credential or rate-limit considerations explicitly so reviewers can reproduce safely.

## Security & Configuration Tips
Never commit populated `env.local` files or real webhook URLs. Rotate Firecrawl/OpenAI keys if monitor logs indicate failures after sharing logs, and prefer GitHub Secrets for automation. Before adding new municipalities, validate the target URLs locally and ensure they do not exceed the Firecrawl free-tier rate (keep requests 4–5 seconds apart, matching `RATE_LIMIT_DELAY`).

## Firecrawl CLI Option
- Firecrawl ships an npm CLI plus an optional Skill for AI agents. Install via `npm install -g firecrawl-cli` and, if you want agent access (Claude Code, Antigravity, etc.), run `npx skills add firecrawl/cli` then restart the agent. Full doc index: <https://docs.firecrawl.dev/llms.txt>.
- Use `firecrawl --status`, `firecrawl map <url>`, and `firecrawl search "grundsalg <region>"` during development to validate URLs before editing `monitor.py`. The CLI respects `FIRECRAWL_API_KEY`, so keep it in `.env.local` or export it when running ad-hoc commands.
