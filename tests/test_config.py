import importlib
from pathlib import Path


def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from socdl import config as cfgmod
    importlib.reload(cfgmod)

    cfg = cfgmod.load()
    assert cfg.language in ("en", "id")

    cfg.quality = "720p"
    cfg.language = "id"
    cfgmod.save(cfg)

    cfg2 = cfgmod.load()
    assert cfg2.quality == "720p"
    assert cfg2.language == "id"


def test_default_output_dir_is_path():
    from socdl import config as cfgmod
    p = cfgmod.default_output_dir()
    assert isinstance(p, Path)
