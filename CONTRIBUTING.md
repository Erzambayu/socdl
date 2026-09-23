# Contributing to socdl

Thanks for taking the time to contribute! 🎉

## Ways to help

- 🐛 **Report bugs** — open an [issue](https://github.com/Erzambayu/socdl/issues) with the URL that failed, the platform, and the full error output.
- 💡 **Suggest features** — open a discussion or issue with the tag `enhancement`.
- 🌐 **Add a language** — copy `src/socdl/i18n/en.py` to `<lang>.py`, translate the strings, register it in `src/socdl/i18n/__init__.py`.
- 🧩 **Add a platform** — add a regex + kind tuple to `src/socdl/platforms.py::PATTERNS` and, if needed, an engine preference in `src/socdl/router.py::engine_chain`.
- 📝 **Improve docs** — README, examples, screenshots — all welcome.

## Dev setup

```bash
git clone https://github.com/Erzambayu/socdl.git
cd socdl
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the tool locally:

```bash
socdl --help
socdl detect https://youtu.be/dQw4w9WgXcQ
```

## Code style

- Line length: 100.
- Formatter/linter: **ruff** (`ruff check .` and `ruff format .`).
- Type hints where they help clarity.
- Prefer small, focused PRs.

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add clipboard watcher for macOS
fix: handle IG reel URLs with query params
docs: fix typo in README
chore: bump yt-dlp minimum version
```

## Pull request checklist

- [ ] Tests pass (`pytest`)
- [ ] Lint passes (`ruff check .`)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] README updated if user-facing behavior changed

## Releasing

> **Rule: every release must ship release notes.** The release workflow fills the
> GitHub Release body from the matching `CHANGELOG.md` section, so a release
> without a changelog entry will silently fall back to auto-generated notes.

1. Make sure `CHANGELOG.md` has a `## [x.y.z] — YYYY-MM-DD` section for the new
   version (this becomes the release body).
2. Bump the version in **both** `pyproject.toml` and `src/socdl/__init__.py`.
3. Commit, then tag and push:

   ```bash
   git add -A
   git commit -m "chore(release): vX.Y.Z"
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```

4. The `Release` workflow builds the Windows/Linux binaries + wheel/sdist,
   publishes to PyPI, and creates the GitHub Release with the changelog as its
   body.

To preview the release body locally:

```bash
python scripts/changelog_for_version.py X.Y.Z
```

## Code of Conduct

Be kind. Assume good intent. No harassment, discrimination, or spam.
