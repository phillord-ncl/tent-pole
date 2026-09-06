from click.testing import CliRunner

from tent_pole import page


def test_dump_writes_tpp_stamp_file(tmp_path):
    """Integration test (CLI dispatch + real file I/O together) that
    needs no Canvas access at all, so it isn't marked `canvas` and runs
    by default alongside the unit tests."""
    target = tmp_path / "example.html"
    target.write_text("<p>hi</p>")

    runner = CliRunner()
    result = runner.invoke(page.page, ["dump", str(target)])

    assert result.exit_code == 0
    assert (tmp_path / "example.tpp").exists()
