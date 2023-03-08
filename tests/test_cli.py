from pathlib import Path

import pytest
from click.testing import CliRunner
from nonebot import require
from nonebug.app import App


def test_cli_help(app: App):
    require("nonebot-bison")
    from nonebot_bison.script.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    print(result.output)
    assert "export" in result.output
