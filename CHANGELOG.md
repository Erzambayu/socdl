# Changelog

All notable changes to **socdl** will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.6] — 2026-09-28

### Fixed
- **Instagram posts and reels could not be downloaded at all (case-sensitivity
  bug)**. URL detection matched its patterns against a *lowercased* copy of the
  URL, so the captured shortcode came out lowercased (`ddrpu-qewtm`) while
  Instagram shortcodes are case-sensitive (`DdrPU-QEwTm`). Instaloader therefore
  looked up a shortcode that does not exist and every attempt failed with
  "Fetching Post metadata failed" — which the fallback engine then reported as
  "Instagram needs login", sending users down the wrong troubleshooting path.
  Detection now matches the original URL case-insensitively, so the target keeps
  its original casing.

### Added
- **`socdl login`** to create a reusable Instagram session, with two ways in:
  - `socdl login --cookies cookies.json` — import cookies exported from a browser
    (JSON array, a JSON object with a `cookies` key, or Netscape `cookies.txt`).
    Only `instagram.com` cookies are kept; `sessionid` and `csrftoken` are
    required.
  - `socdl login --username you` — interactive instaloader login.
  - `socdl login --status` shows whether a saved session exists;
    `socdl logout` deletes it.
- The session is stored as a pickle in the platform data directory
  (`instagram.session`) and is reused automatically by both the in-process and
  subprocess download paths, so private and age-gated posts resolve on the first
  engine in the chain.

### Changed
- `Config.instagram_login` is now documented and treated strictly as a *session
  file path*. It was previously passed to instaloader's
  `load_session_from_file()`, whose first argument is a **username**, and to
  `instaloader --login`, which likewise takes a username — so setting it never
  loaded a session.
- The login hint no longer points at `socdl config`, which only edits
  configuration and never creates a session.

## [0.1.5] — 2026-09-23

### Added
- **Media info panel**: before each download, socdl now shows an info panel with
  title, uploader, duration, date and engagement counters (**views, likes,
  comments, shares/reposts**) whenever the source exposes them (YouTube, TikTok,
  Facebook, X, Instagram, …). Missing fields are simply hidden.
- **`/info <url>` command** to look up a link's details without downloading
  (falls back to the last pasted URL when no argument is given).
- Engagement counters are **persisted to history**: `/history` now shows
  Views / Likes / Comments columns (only when data is available). Existing
  databases are migrated automatically.
- Best-effort metadata via a new `probe()` step in the engines/router: yt-dlp
  (metadata extraction) and instaloader (Instagram like/comment counts).

## [0.1.4] — 2026-09-23

### Added
- **Real download progress bar**: a live bar with percentage, transferred/total
  size, speed and ETA. Works both for the subprocess engine (parsed from a
  machine-readable `--progress-template` line) and the in-process yt-dlp API
  (via `progress_hooks`).
- **Download queue**: multiple pasted links are now queued instead of firing all
  at once. Manage it with `/queue add <url>`, `/queue run`, `/queue list` and
  `/queue clear`. Single links still download immediately.

### Fixed
- **Facebook support**: far more link forms are now recognised (`fb.watch`,
  `/<user>/videos/<id>`, `/share/r|v/<code>`, group posts, `photo?fbid=`,
  `permalink.php`, `m.facebook.com`, `web.facebook.com`, …) instead of falling
  through to "unknown". A short hint is shown when Facebook asks for a login.
- **Portrait / reel videos failed at non-"best" quality**. The quality filters
  used `height<=N`, but for vertical videos (Facebook reels, YouTube Shorts,
  TikTok) the *height* is the long side, so nothing matched and the download
  aborted with "Requested format is not available". Filters now cap both
  dimensions and always fall back to the best available format.
- Facebook now routes to `yt-dlp` only (gallery-dl has no Facebook extractor),
  avoiding a pointless fallback attempt and a misleading final error.

### Changed
- Engines accept an optional progress callback; the router now distinguishes the
  engine-switch callback (`on_engine`) from byte-level progress (`progress_cb`).
- In-process yt-dlp output is silenced while our own progress bar is active, so
  the two no longer interleave.

## [0.1.3] — 2026-09-17

### Changed
- Bumped GitHub Actions to current majors to silence Node.js 20 deprecation
  warnings: `checkout` v7, `setup-python` v7, `upload-artifact` v7,
  `download-artifact` v8, `action-gh-release` v3.

## [0.1.2] — 2026-09-17

### Added
- `/stats` command — summary of total / successful / failed downloads plus a per-platform breakdown.
- `/clear` command to wipe the terminal inside the interactive shell.
- `/clip [value]` to copy the last download result (or a literal string) to the clipboard.
- Feedback messages for every interactive command, so it is always clear what happened.

### Fixed
- Interactive prompt no longer overlaps with panel/table output (pending output is flushed before reading input).
- `/open` (and `/config`) now report failures instead of silently doing nothing, and no longer stack output on top of the prompt.
- `/stats` no longer crashes due to an unsupported `title_style` argument passed to Rich's `Panel`.

## [0.1.1] — 2026-09-17

### Changed
- Enabled PyPI Trusted Publishing so tagged releases are automatically
  uploaded to <https://pypi.org/project/socdl/>.

## [0.1.0] — 2026-09-17

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
