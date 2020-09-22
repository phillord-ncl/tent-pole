import appdirs
import click
import dpath.util
import functools
import os
import toml

from canvasapi import Canvas

def fetch_config(files):
    files = [toml.load(f) for f in files if os.path.exists(f)]
    ## merge here does a deep merge, otherwise one section will overload another
    return functools.reduce(dpath.util.merge, files)

def config_config():
    return fetch_config(
        [
            appdirs.user_config_dir("tent-pole") + "/tent-pole.toml",
            "./tent-pole.toml"
        ]
    )

def config_course():
    return dpath.util.get(CONFIG, "general/course")

def config_course_obj():
    return config_canvas().get_course(config_course())

def config_api_key():
    return dpath.util.get(CONFIG, "general/api_key")

def config_canvas():
    return Canvas(API_URL, config_api_key())


API_URL="https://ncl.instructure.com"
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
