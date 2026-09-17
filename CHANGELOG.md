# Changelog

All notable changes to **socdl** will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-01-XX

### Added
- First public release.
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
