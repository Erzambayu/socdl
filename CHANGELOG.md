# Changelog

All notable changes to **socdl** will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.2] — 2026-01-XX

### Added
- `/stats` command — summary of total / successful / failed downloads plus a per-platform breakdown.
- `/clear` command to wipe the terminal inside the interactive shell.
- `/clip [value]` to copy the last download result (or a literal string) to the clipboard.
- Feedback messages for every interactive command, so it is always clear what happened.

### Fixed
- Interactive prompt no longer overlaps with panel/table output (pending output is flushed before reading input).
- `/open` (and `/config`) now report failures instead of silently doing nothing, and no longer stack output on top of the prompt.
- `/stats` no longer crashes due to an unsupported `title_style` argument passed to Rich's `Panel`.

## [0.1.1] — 2026-01-XX

### Changed
- Enabled PyPI Trusted Publishing so tagged releases are automatically
  uploaded to <https://pypi.org/project/socdl/>.

## [0.1.0] — 2026-01-XX

### Added
- First public release.
- **Standalone binaries** for Windows (x64) and Linux (x64) built with PyInstaller — no Python required.
- **One-liner installers**: `install.ps1` (Windows) and `install.sh` (Linux/macOS), with automatic fallback to `pip`.
- Engines can now run **in-process** (calling the yt-dlp / gallery-dl / instaloader APIs directly) when no external executable is available, so frozen binaries are fully self-contained.
- Automatic ffmpeg discovery, including well-known install locations (winget, scoop, choco, homebrew).
- Interactive Rich TUI with slash commands (`/help`, `/history`, `/watch`, `/paste`, `/open`, `/config`, `/lang`).
- Multi-engine router: **instaloader** for Instagram, **yt-dlp** for YouTube / TikTok video / Facebook, **gallery-dl** for Instagram carousel photos, TikTok photo slides, Twitter/X, Reddit.
- Platform detection with content-kind awareness (post, reel, story, profile, video, photo, playlist).
- Config file at platform-appropriate user config dir (`~/.config/socdl/config.toml` etc.).
- SQLite download history + `socdl history` subcommand.
- Clipboard watcher (`socdl watch`).
- Batch download from text file (`socdl -f links.txt`).
- Auto-update notifier (checks PyPI once per run).
- Bilingual UI: English + Bahasa Indonesia (`--lang en|id`).
- Quality presets: `best | 1080p | 720p | 480p | 360p | audio` (MP3 extract).
- `socdl detect <url>` for debugging.
- `socdl update` to upgrade underlying downloaders.
