import appdirs
import click
import dpath
import functools
import os
import toml

from canvasapi import Canvas

def get_maybe(config,key):
    try:
        return dpath.get(config, key)
    except KeyError:
        return None

def fetch_config(files):
    files = [toml.load(f) for f in files if os.path.exists(f)]
    ## merge here does a deep merge, otherwise one section will overload another
    ## initial {} means "no config file anywhere" returns an empty config
    ## instead of crashing (functools.reduce has no sane default over an
    ## empty sequence otherwise)
    ## MergeType.REPLACE: dpath's default (MergeType.ADDITIVE) concatenates
    ## list-valued keys instead of letting the closer file win, so e.g. a
    ## subdirectory's [module] items would get silently appended to an
    ## ancestor's rather than replacing it -- breaks the cascade's whole
    ## "closest wins" contract for any list-valued key.
    return functools.reduce(
        lambda dst, src: dpath.merge(dst, src, flags=dpath.MergeType.REPLACE),
        files, {}
    )

def ancestor_config_paths(start_dir=None):
    """Every tent-pole.toml from the nearest enclosing git repo root down
    to start_dir (default: the current directory), root-most first.
    Merging in this order means the most specific file (closest to
    start_dir) wins on any conflicting key -- so a course repo can set
    e.g. course/id once at its root and have every subproject directory
    inherit it, overriding only what a deeper directory actually needs
    to override.

    Stops walking upward as soon as a directory containing .git is found
    (inclusive of that directory) -- either a real repo (.git/) or a
    worktree (.git file pointing at the shared repo, which os.path.exists
    matches just as well). Deliberately never crawls all the way to the
    filesystem root: if no .git boundary is found above start_dir at all,
    there's no cascade -- just start_dir itself -- rather than risk
    picking up an unrelated tent-pole.toml from outside the project."""
    start = os.path.abspath(start_dir or os.getcwd())
    dirs = [start]
    current = start
    while not os.path.exists(os.path.join(current, ".git")):
        parent = os.path.dirname(current)
        if parent == current:
            return [os.path.join(start, "tent-pole.toml")]
        current = parent
        dirs.append(current)
    dirs.reverse()
    return [os.path.join(d, "tent-pole.toml") for d in dirs]

def config_config():
    return fetch_config(
        [appdirs.user_config_dir("tent-pole") + "/tent-pole.toml"]
        + ancestor_config_paths()
    )

def use_test_config():
    """Opt-in either way: the TENT_POLE_USE_TEST_CONFIG env var (set by
    --beta, or exported by a course repo's Makefile), or a bare
    top-level `beta = true` in tent-pole.toml. The config-file route
    matters because a Makefile-only env var is silently bypassed by any
    direct CLI call that doesn't go through make -- exactly how a
    module create once landed on production instead of beta. Never a
    silent fallback beyond these two explicit opt-ins."""
    return (
        bool(os.environ.get("TENT_POLE_USE_TEST_CONFIG"))
        or bool(get_maybe(CONFIG, "beta"))
    )

def config_course():
    if use_test_config():
        return config_test_course_id()
    return (
        get_maybe(CONFIG, "course/id") or
        get_maybe(CONFIG, "course/identifier")
    )

def config_module():
    return (
        get_maybe(CONFIG, "module/id") or
        get_maybe(CONFIG, "module/identifier")
    )

def config_module_items():
    return dpath.get(CONFIG, "module/items")

def config_api_key():
    if use_test_config():
        ## Not config_test_api_key(): that falls back to config_api_key(),
        ## which would recurse back here.
        return get_maybe(CONFIG, "dev/test_api_key")
    return get_maybe(CONFIG, "general/api_key")

def config_api_url():
    if use_test_config():
        return config_test_api_url()
    return get_maybe(CONFIG, "general/api_url")

## Tracks the Requester behind the most recently created Canvas
## connection, purely so a CanvasException's real response
## (body/headers) can be recovered after the fact -- canvasapi's own
## generic error branch discards both, keeping only the status code
## (see main.cli). Requester already caches its last 5 responses
## regardless of what any exception carries; this just keeps a handle
## on which one to ask.
##
## Canvas stores its Requester under a name-mangled attribute
## (_Canvas__requester, since Canvas's own __init__ sets self.__requester
## from inside the class) -- unlike a Course/Page/etc, which get handed
## the same Requester and store it as a plain _requester. Extracting it
## here, once, keeps that private-attribute reliance in one place.
_last_requester = None

def config_canvas():
    global _last_requester
    api_url = config_api_url()
    api_key = config_api_key()
    missing = [
        name for name, value in (("api_url", api_url), ("api_key", api_key))
        if not value
    ]
    if missing:
        ## canvasapi's own Canvas.__init__ does `"api/v1" in base_url`
        ## unconditionally, so a None api_url crashes with a raw
        ## TypeError from inside canvasapi rather than any message
        ## about config at all -- check first and say which key,
        ## under which config path, is actually missing.
        prefix = "dev/test_" if use_test_config() else "general/"
        raise click.ClickException(
            "Canvas not configured: {} not set (targeting {} -- "
            "looked for {}). Check tent-pole.toml and "
            "~/.config/tent-pole/tent-pole.toml.".format(
                " and ".join(missing),
                "beta/test" if use_test_config() else "production",
                ", ".join(prefix + m for m in missing),
            )
        )
    canvas = Canvas(api_url, api_key)
    _last_requester = canvas._Canvas__requester
    return canvas

def last_response():
    """The most recent raw HTTP response canvasapi received, if any."""
    if _last_requester is None:
        return None
    cache = _last_requester._cache
    return cache[0] if cache else None

def config_current_user_id():
    """The Canvas user id tent-pole's own API key authenticates as --
    used to tell tent-pole's own edits apart from someone else's when
    checking a page's last_edited_by."""
    return config_canvas().get_current_user().id

def config_test_api_key():
    return get_maybe(CONFIG, "dev/test_api_key") or config_api_key()

def config_test_course_id():
    return get_maybe(CONFIG, "dev/test_course_id")

def config_test_api_url():
    return get_maybe(CONFIG, "dev/test_api_url")

def config_test_canvas():
    ## Deliberately no fallback to config_api_url(): tests must have an
    ## explicit target (e.g. beta) so a missing config value can never
    ## silently mean "run against the live instance".
    return Canvas(config_test_api_url(), config_test_api_key())


CONFIG = config_config()

## CLI

@click.group()
def config():
    pass

@config.command()
def api_key():
    print(config_api_key())

@config.command()
def dump():
    print(CONFIG)

@config.command()
def course():
    print(config_course())

@config.command(name="api-url")
def api_url():
    print(config_api_url())
