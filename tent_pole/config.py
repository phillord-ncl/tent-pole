import appdirs
import click
import dpath.util
import functools
import os
import toml

from canvasapi import Canvas

def get_maybe(config,key):
    try:
        return dpath.util.get(config, key)
    except KeyError:
        return None

def fetch_config(files):
    files = [toml.load(f) for f in files if os.path.exists(f)]
    ## merge here does a deep merge, otherwise one section will overload another
    ## initial {} means "no config file anywhere" returns an empty config
    ## instead of crashing (functools.reduce has no sane default over an
    ## empty sequence otherwise)
    return functools.reduce(dpath.util.merge, files, {})

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

def config_course():
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
    return dpath.util.get(CONFIG, "module/items")

def config_api_key():
    return dpath.util.get(CONFIG, "general/api_key")

def config_api_url():
    return get_maybe(CONFIG, "general/api_url") or DEFAULT_API_URL

def config_canvas():
    return Canvas(config_api_url(), config_api_key())

def config_test_api_key():
    return get_maybe(CONFIG, "dev/test_api_key") or config_api_key()

def config_test_course_id():
    return get_maybe(CONFIG, "dev/test_course_id")

def config_test_api_url():
    return get_maybe(CONFIG, "dev/test_api_url")

def config_test_canvas():
    ## Deliberately no fallback to config_api_url()/DEFAULT_API_URL: tests
    ## must have an explicit target (e.g. beta) so a missing config value
    ## can never silently mean "run against the live instance".
    return Canvas(config_test_api_url(), config_test_api_key())


DEFAULT_API_URL = "https://ncl.instructure.com"
CONFIG = config_config()

## CLI

@click.group()
def config():
    pass

@config.command()
def api_key():
    print(config_api_key(CONFIG))

@config.command()
def dump():
    print(CONFIG)

@config.command()
def course():
    print(config_course(CONFIG))
