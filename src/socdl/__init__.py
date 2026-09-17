"""socdl - Social media downloader CLI.

A friendly, fast command-line tool to download photos & videos from
Instagram, TikTok, YouTube, Twitter/X, Reddit, Facebook and more.
"""

__version__ = "0.1.2"
__author__ = "Erzam Bayu"
__license__ = "MIT"
__url__ = "https://github.com/Erzambayu/socdl"

from .platforms import detect_platform  # re-export for convenience

__all__ = ["__version__", "detect_platform"]
