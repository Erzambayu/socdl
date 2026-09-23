<div align="center">

# socdl

**Social media downloader for humans.**
_Instagram · TikTok · YouTube · Twitter/X · Reddit · Facebook_

[![PyPI](https://img.shields.io/pypi/v/socdl.svg?color=blue)](https://pypi.org/project/socdl/)
[![Python](https://img.shields.io/pypi/pyversions/socdl.svg)](https://pypi.org/project/socdl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/Erzambayu/socdl/actions/workflows/ci.yml/badge.svg)](https://github.com/Erzambayu/socdl/actions)

_Read this in another language: [🇮🇩 Bahasa Indonesia](#-bahasa-indonesia)_

</div>

---

## ✨ Highlights

- **One command for every platform.** Paste any link — socdl picks the best engine automatically.
- **Handles carousels properly.** Instagram photo + video posts? All items downloaded, not just the video.
- **Clean folders.** Organized by platform → uploader → dated filename. No mess.
- **Beautiful TUI.** Rich progress bars, colored tables, banners. Feels good to use.
- **Interactive or one-shot.** Run `socdl` for a REPL, or `socdl <url>` and go.
- **Clipboard watcher.** `socdl watch` — copy a link, it downloads. That's it.
- **Batch mode.** `socdl -f links.txt` — download hundreds of links at once.
- **History log.** `socdl history` — see everything you've grabbed.
- **Bilingual.** English + Bahasa Indonesia (`--lang en|id`).

## 📦 Install

### ⚡ One-liner (no Python required)

**Windows** (PowerShell):

```powershell
irm https://raw.githubusercontent.com/Erzambayu/socdl/main/install.ps1 | iex
```

**Linux / macOS** (bash):

```bash
curl -fsSL https://raw.githubusercontent.com/Erzambayu/socdl/main/install.sh | bash
```

The installers download the standalone binary from the latest
[release](https://github.com/Erzambayu/socdl/releases), put it on your `PATH`,
and fall back to `pip` automatically if a binary isn't available.

### 🐍 Via Python package managers

```bash
pip install socdl
```

Or with [pipx](https://pipx.pypa.io/) (recommended, isolated env):

```bash
pipx install socdl
```

### 📥 Manual download (standalone binary)

Grab the binary for your platform from the
[latest release](https://github.com/Erzambayu/socdl/releases/latest):

| Platform      | Asset                    |
|---------------|--------------------------|
| Windows x64   | `socdl-windows-x64.exe`  |
| Linux x64     | `socdl-linux-x64`        |

```bash
# Linux — make it executable and run
chmod +x socdl-linux-x64
./socdl-linux-x64 --help
```

**Requirements:** _none_ for the standalone binary. For `pip` install you need
Python 3.9+. Either way, [ffmpeg](https://ffmpeg.org/) is **optional but
recommended** for best YouTube quality.

<details>
<summary><b>Installing ffmpeg</b></summary>

| OS      | Command                                    |
|---------|--------------------------------------------|
| Windows | `winget install Gyan.FFmpeg`               |
| macOS   | `brew install ffmpeg`                      |
| Linux   | `sudo apt install ffmpeg` / your distro    |

</details>

## 🚀 Quick start

**Interactive mode** — just run:

```bash
socdl
```

Paste any link, press Enter — done.

**One-shot mode:**

```bash
socdl https://www.instagram.com/p/XXXX/
socdl https://youtu.be/XXXX https://vt.tiktok.com/XXXX
```

**Batch from file:**

```bash
socdl -f my-links.txt
```

**Clipboard watcher** (auto-download on copy):

```bash
socdl watch
```

## 🎛️ Commands

| Command                 | Description                                                |
|-------------------------|------------------------------------------------------------|
| `socdl`                 | Launch interactive TUI                                     |
| `socdl <url> [<url>…]`  | Download URLs directly                                     |
| `socdl -f links.txt`    | Batch download from file                                   |
| `socdl watch`           | Clipboard watcher                                          |
| `socdl history`         | Show recent downloads                                      |
| `socdl config`          | Show config; use `--set key=value` to edit                 |
| `socdl update`          | Upgrade yt-dlp / instaloader / gallery-dl                  |
| `socdl detect <url>`    | Debug: print detected platform / kind                      |

**Options** (available on the main command):

```
-o, --output PATH        Override output directory
-q, --quality LEVEL      best | 1080p | 720p | 480p | 360p | audio
    --lang {en,id}       Force UI language
-f, --file PATH          Batch mode from text file
-V, --version            Show version
```

**Interactive slash commands** (inside `socdl`):

```
/help           Show help
/config         Open config file
/history        Show recent downloads
/stats          Show download statistics
/queue add URL  Queue one or more links
/queue run      Download everything in the queue
/queue list     Show the queue
/queue clear    Empty the queue
/info [url]     Show likes/comments/shares for a link
/watch          Start clipboard watcher
/paste          Download URL from clipboard
/clip [value]   Copy last result (or a value) to clipboard
/open [path]    Open downloads folder (or a path)
/clear          Clear the screen
/lang en|id     Switch UI language
/quit           Exit
```

> **Tip:** paste several links at once and they are queued automatically — run
> `/queue run` when you are ready. Every download shows a live progress bar with
> speed and ETA, plus an info panel with views / likes / comments / shares when
> the source provides them.

## ⚙️ Configuration

Config lives at:

- **Linux/macOS:** `~/.config/socdl/config.toml`
- **Windows:** `%APPDATA%\socdl\config.toml`

Sample:

```toml
output_dir             = ""              # empty = ~/Downloads/socdl-downloads
subfolder_per_platform = true
subfolder_per_uploader = true

language               = "en"            # "en" | "id"
quality                = "best"          # best|1080p|720p|480p|360p|audio
embed_metadata         = true
embed_thumbnail        = true
concurrent_fragments   = 4
restrict_filenames     = true

check_updates          = true
log_history            = true

instagram_login        = ""              # your IG username (for private/story)
cookies_from_browser   = ""              # "" | chrome | firefox | edge | brave
```

Edit inline:

```bash
socdl config --set quality=1080p
socdl config --set language=id
socdl config --set output_dir=D:/media
socdl config --show
```

## 🔐 Private / login-required content

For Instagram stories, private accounts, age-restricted YouTube, etc.:

**Instagram** — one-time login via instaloader:

```bash
socdl config --set instagram_login=your_username
instaloader -l your_username    # asks password, saves session
```

**YouTube / X / Reddit** — reuse your browser cookies:

```bash
socdl config --set cookies_from_browser=chrome
```

Supported browsers: `chrome`, `firefox`, `edge`, `brave`, `opera`, `vivaldi`.

## 🗂️ Folder structure

```
~/Downloads/socdl-downloads/
├── Instagram/<username>/2024-01-15_ABCDEF_1.jpg
├── TikTok/<username>/2024-01-15_video-title.mp4
├── YouTube/<uploader>/Video Title [XXXX].mp4
├── Twitter/<username>/2024-01-15_tweetid_1.jpg
└── Reddit/<subreddit>/postid_01.jpg
```

## 🌍 Supported sites

Core:

- **Instagram** — posts, reels, carousels (photo+video), profile scrape, stories\*
- **TikTok** — videos, photo slides, profiles
- **YouTube** — videos, shorts, playlists
- **Twitter/X** — tweets with images/video, threads
- **Reddit** — posts (image, video, galleries)
- **Facebook** — public videos and posts\*

\* May require login/cookies. See [Private content](#-private--login-required-content).

Plus **1000+ other sites** via yt-dlp fallback (Twitch clips, Vimeo, SoundCloud, …).

## 🧑‍💻 Development

```bash
git clone https://github.com/Erzambayu/socdl.git
cd socdl
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
socdl --help
```

Run tests / lint:

```bash
pytest
ruff check .
```

## 🤝 Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

MIT © [Erzam Bayu](https://github.com/Erzambayu)

---

## 🇮🇩 Bahasa Indonesia

**socdl** — downloader sosmed yang ramah manusia. Instagram, TikTok, YouTube, Twitter/X, Reddit, Facebook — semua dari satu command.

### Kenapa socdl?

- Paste link apa aja, socdl otomatis pilih engine yang paling cocok.
- **Instagram carousel foto+video?** Semua item ke-download, bukan cuma video-nya.
- Folder rapi otomatis: platform → uploader → tanggal.
- TUI cakep pake Rich (progress bar, tabel warna).
- Bisa interactive (`socdl`) atau one-shot (`socdl <link>`).
- **Clipboard watcher** — copy link, langsung download. Ga usah bolak-balik terminal.
- Batch dari file `.txt`, history log SQLite, auto-update checker.
- **Bilingual** — bisa English atau Indonesia (`--lang id`).

### Install

**One-liner (tanpa Python):**

```powershell
# Windows (PowerShell):
irm https://raw.githubusercontent.com/Erzambayu/socdl/main/install.ps1 | iex
```

```bash
# Linux / macOS:
curl -fsSL https://raw.githubusercontent.com/Erzambayu/socdl/main/install.sh | bash
```

Atau download manual binary dari [Releases](https://github.com/Erzambayu/socdl/releases/latest).

**Via pip:**

```bash
pip install socdl
# atau (lebih rapi):
pipx install socdl
```

Butuh ffmpeg (opsional tapi disaranin). Binary standalone ga butuh Python.

### Pake

```bash
# Mode interactive (paling enak):
socdl --lang id

# One-shot:
socdl https://www.instagram.com/p/XXXX/

# Batch dari file:
socdl -f links.txt

# Auto-download apapun yang lo copy:
socdl watch
```

### Config

Edit gampang:

```bash
socdl config --set language=id
socdl config --set quality=1080p
socdl config --set output_dir=D:/downloads
socdl config --show
```

### Konten private (story IG, dll)

```bash
# Instagram
socdl config --set instagram_login=username_lo
instaloader -l username_lo   # login sekali, sesi tersimpan

# YouTube/X/Reddit — pake cookies browser:
socdl config --set cookies_from_browser=chrome
```

### Support

Ada bug atau request? Buka [issue di GitHub](https://github.com/Erzambayu/socdl/issues).

---

<div align="center">

Made with ❤️ by [Erzam Bayu](https://github.com/Erzambayu)

</div>
