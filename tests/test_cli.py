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


def test_interactive_help_then_quit():
    r = CliRunner().invoke(cli, [], input="/help\n/quit\n")
    assert r.exit_code == 0
    assert "/stats" in r.output


def test_interactive_stats_does_not_crash():
    r = CliRunner().invoke(cli, [], input="/stats\n/quit\n")
    assert r.exit_code == 0
    assert r.exception is None


def test_interactive_unknown_command():
    r = CliRunner().invoke(cli, [], input="/nope\n/quit\n")
    assert r.exit_code == 0
    assert "/nope" in r.output


def test_interactive_lang_switch():
    r = CliRunner().invoke(cli, [], input="/lang en\n/quit\n")
    assert r.exit_code == 0
    r2 = CliRunner().invoke(cli, [], input="/lang id\n/quit\n")
    assert r2.exit_code == 0


def test_interactive_queue_empty_list():
    r = CliRunner().invoke(cli, [], input="/queue\n/quit\n")
    assert r.exit_code == 0
    assert r.exception is None


def test_interactive_queue_add_and_list():
    r = CliRunner().invoke(
        cli, [], input="/queue add https://youtu.be/dQw4w9WgXcQ\n/queue list\n/quit\n"
    )
    assert r.exit_code == 0
    assert "youtu.be" in r.output


def test_interactive_queue_add_many_via_paste():
    inp = "https://youtu.be/a https://youtu.be/b\n/queue list\n/quit\n"
    r = CliRunner().invoke(cli, [], input=inp)
    assert r.exit_code == 0
    assert r.exception is None
    # both links should be listed in the queue table
    assert "youtu.be/a" in r.output and "youtu.be/b" in r.output


def test_interactive_queue_clear():
    r = CliRunner().invoke(
        cli, [], input="/queue add https://youtu.be/x\n/queue clear\n/queue list\n/quit\n"
    )
    assert r.exit_code == 0
    assert r.exception is None


def test_interactive_queue_usage_on_bad_sub():
    r = CliRunner().invoke(cli, [], input="/queue bogus\n/quit\n")
    assert r.exit_code == 0
    assert r.exception is None


def test_interactive_queue_run_empty():
    r = CliRunner().invoke(cli, [], input="/queue run\n/quit\n")
    assert r.exit_code == 0
    assert r.exception is None
