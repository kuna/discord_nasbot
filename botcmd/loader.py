import importlib.util
import inspect
import sys
from pathlib import Path

from discord.ext import commands

from botcmd.dispatcher import DiscordCommandDispatcher
from botcmd.logs import logger

PLUGIN_DIRS = ["plugins", "plugins_priv"]


def _make_channel_check(channels):
    async def predicate(ctx):
        return not channels or ctx.channel.name in channels

    return predicate


def _make_callback(instance):
    # discord.py rejects bound methods as command callbacks, so wrap in a plain function.
    # discord.py parses command arguments from the callback signature, so only expose
    # *args when the handler actually accepts them.
    accepts_args = any(
        p.kind is inspect.Parameter.VAR_POSITIONAL
        for p in inspect.signature(instance.handler).parameters.values()
    )

    if accepts_args:

        async def callback(ctx, *args):
            await instance.handler(ctx, *args)

    else:

        async def callback(ctx):
            await instance.handler(ctx)

    callback.__doc__ = instance.handler.__doc__
    return callback


def _import_handler(base, name, path):
    module_name = f"{base}.{name}.handler"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _is_dispatcher(obj):
    return (
        inspect.isclass(obj)
        and issubclass(obj, DiscordCommandDispatcher)
        and obj is not DiscordCommandDispatcher
        and (obj.command or obj.cron)
    )


def _register_dispatchers(bot, module, dep=None, scheduler=None):
    registered = []
    for obj in vars(module).values():
        if not _is_dispatcher(obj):
            continue
        instance = obj(bot, dep)
        if obj.command:
            command = commands.Command(
                _make_callback(instance),
                name=obj.command,
                checks=[_make_channel_check(obj.channel)],
            )
            bot.add_command(command)
            registered.append(obj.command)
        if obj.cron:
            if scheduler is None:
                logger.warning(
                    "Plugin class '%s' declares cron %r but no scheduler is available",
                    obj.__name__,
                    obj.cron,
                )
            elif scheduler.add(instance):
                registered.append(f"cron:{obj.cron}")
    return registered


def load_plugins(bot, disabled_plugins=None, root=None, dep=None, scheduler=None):
    """Discover and register plugins from PLUGIN_DIRS under root (default: repo root).

    disabled_plugins is a comma-separated string of plugin folder names to skip.
    dep is the shared Dependency object handed to every dispatcher (see depend.py).
    scheduler collects dispatchers that declare a cron expression.
    Returns the list of loaded plugin names.
    """
    disabled = {p.strip() for p in (disabled_plugins or "").split(",") if p.strip()}
    root = Path(root) if root else Path(__file__).resolve().parent.parent
    loaded = []
    for base in PLUGIN_DIRS:
        base_dir = root / base
        if not base_dir.is_dir():
            continue
        for handler_path in sorted(base_dir.glob("*/handler.py")):
            name = handler_path.parent.name
            if name in disabled:
                logger.info("Plugin '%s' is disabled, skipping", name)
                continue
            module = _import_handler(base, name, handler_path)
            names = _register_dispatchers(bot, module, dep, scheduler)
            logger.info("Loaded plugin '%s' (commands: %s)", name, ", ".join(names) or "none")
            loaded.append(name)
    return loaded
