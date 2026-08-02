from types import SimpleNamespace

import discord
import pytest
from discord.ext import commands

from botcmd.loader import _make_channel_check, load_plugins

PLUGIN_TEMPLATE = """
from botcmd.dispatcher import DiscordCommandDispatcher


class Dispatcher(DiscordCommandDispatcher):
    command = "{command}"
    channel = {channel}

    async def handler(self, ctx):
        await ctx.send("hello from {command}")
"""


def make_bot():
    return commands.Bot(command_prefix="!", intents=discord.Intents.default())


def make_plugin(root, name, command=None, channel=(), base="plugins"):
    plugin_dir = root / base / name
    plugin_dir.mkdir(parents=True)
    content = PLUGIN_TEMPLATE.format(command=command or name, channel=list(channel))
    (plugin_dir / "handler.py").write_text(content)


def test_load_plugins_registers_commands(tmp_path):
    make_plugin(tmp_path, "hello")
    make_plugin(tmp_path, "bye")

    bot = make_bot()
    loaded = load_plugins(bot, root=tmp_path)

    assert loaded == ["bye", "hello"]
    assert bot.get_command("hello") is not None
    assert bot.get_command("bye") is not None


def test_private_plugins_are_loaded(tmp_path):
    make_plugin(tmp_path, "secret", base="plugins_priv")

    bot = make_bot()
    loaded = load_plugins(bot, root=tmp_path)

    assert loaded == ["secret"]
    assert bot.get_command("secret") is not None


def test_disabled_plugins_are_skipped(tmp_path):
    make_plugin(tmp_path, "hello")
    make_plugin(tmp_path, "bye")

    bot = make_bot()
    loaded = load_plugins(bot, disabled_plugins="hello", root=tmp_path)

    assert loaded == ["bye"]
    assert bot.get_command("hello") is None
    assert bot.get_command("bye") is not None


def test_disabled_plugins_tolerates_spaces_and_empties(tmp_path):
    make_plugin(tmp_path, "hello")

    bot = make_bot()
    loaded = load_plugins(bot, disabled_plugins=" hello , ,other,", root=tmp_path)

    assert loaded == []
    assert bot.get_command("hello") is None


def test_missing_plugin_dirs_are_ignored(tmp_path):
    bot = make_bot()
    assert load_plugins(bot, root=tmp_path) == []


def test_folder_without_handler_is_ignored(tmp_path):
    (tmp_path / "plugins" / "empty").mkdir(parents=True)

    bot = make_bot()
    assert load_plugins(bot, root=tmp_path) == []


@pytest.mark.asyncio
async def test_registered_command_sends_response(tmp_path):
    make_plugin(tmp_path, "hello")

    bot = make_bot()
    load_plugins(bot, root=tmp_path)

    sent = []
    ctx = SimpleNamespace(send=lambda msg: _record(sent, msg))
    await bot.get_command("hello").callback(ctx)
    assert sent == ["hello from hello"]


async def _record(sink, msg):
    sink.append(msg)


ARGS_PLUGIN = """
from botcmd.dispatcher import DiscordCommandDispatcher


class Dispatcher(DiscordCommandDispatcher):
    command = "shout"

    async def handler(self, ctx, *args):
        await ctx.send(" ".join(args).upper())
"""


@pytest.mark.asyncio
async def test_handler_with_var_args_receives_them(tmp_path):
    plugin_dir = tmp_path / "plugins" / "shout"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "handler.py").write_text(ARGS_PLUGIN)

    bot = make_bot()
    load_plugins(bot, root=tmp_path)
    command = bot.get_command("shout")

    # discord.py feeds each word to the var-positional param of the callback
    assert any(p.kind is p.VAR_POSITIONAL for p in command.params.values())

    sent = []
    ctx = SimpleNamespace(send=lambda msg: _record(sent, msg))
    await command.callback(ctx, "hello", "world")
    assert sent == ["HELLO WORLD"]


def test_handler_without_var_args_keeps_plain_signature(tmp_path):
    make_plugin(tmp_path, "hello")

    bot = make_bot()
    load_plugins(bot, root=tmp_path)

    # no var-positional param exposed, so discord.py ignores extra words
    params = bot.get_command("hello").params
    assert not any(p.kind is p.VAR_POSITIONAL for p in params.values())


DEP_PLUGIN = """
from botcmd.dispatcher import DiscordCommandDispatcher


class Dispatcher(DiscordCommandDispatcher):
    command = "show_dep"

    async def handler(self, ctx):
        await ctx.send(self.dep)
"""


@pytest.mark.asyncio
async def test_dep_is_passed_to_dispatchers(tmp_path):
    plugin_dir = tmp_path / "plugins" / "show_dep"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "handler.py").write_text(DEP_PLUGIN)

    bot = make_bot()
    load_plugins(bot, root=tmp_path, dep="the-shared-dep")

    sent = []
    ctx = SimpleNamespace(send=lambda msg: _record(sent, msg))
    await bot.get_command("show_dep").callback(ctx)
    assert sent == ["the-shared-dep"]


@pytest.mark.asyncio
async def test_channel_check():
    ctx_in_bot = SimpleNamespace(channel=SimpleNamespace(name="bot"))
    ctx_in_general = SimpleNamespace(channel=SimpleNamespace(name="general"))

    restricted = _make_channel_check(["bot"])
    assert await restricted(ctx_in_bot) is True
    assert await restricted(ctx_in_general) is False

    unrestricted = _make_channel_check([])
    assert await unrestricted(ctx_in_bot) is True
    assert await unrestricted(ctx_in_general) is True


@pytest.mark.asyncio
async def test_registered_command_has_channel_check(tmp_path):
    make_plugin(tmp_path, "hello", channel=["bot"])

    bot = make_bot()
    load_plugins(bot, root=tmp_path)
    command = bot.get_command("hello")

    ctx_in_bot = SimpleNamespace(channel=SimpleNamespace(name="bot"))
    ctx_in_general = SimpleNamespace(channel=SimpleNamespace(name="general"))
    assert await command.checks[0](ctx_in_bot) is True
    assert await command.checks[0](ctx_in_general) is False
