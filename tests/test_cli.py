from click.testing import CliRunner

from socdl.cli import cli


def test_help():
    r = CliRunner().invoke(cli, ["--help"])
    assert r.exit_code == 0
    assert "socdl" in r.output


def test_version():
    r = CliRunner().invoke(cli, ["--version"])
    assert r.exit_code == 0


def test_detect_subcommand():
    r = CliRunner().invoke(cli, ["detect", "https://youtu.be/dQw4w9WgXcQ"])
    assert r.exit_code == 0
    assert "youtube" in r.output.lower()
