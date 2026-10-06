import click
import os
import time
import toml

from . import config
from . import course
from . import manifest

## Fixed, not configurable -- every file tent-pole uploads lands here,
## rather than Canvas's generic default "unfiled" folder, so "did
## tent-pole manage this" remains a cheap folder_id check. Local
## subdirectories are recreated beneath this managed root.
TENT_POLE_FOLDER = "tent-pole"

def __canvasfilename_from_path(path):
    return os.path.basename(path)


def __course_relative_path(filename):
    """Path beneath the course's git root, without allowing uploads
    outside that root. The root is config.git_root(), not os.getcwd():
    a file command run from inside a nested module directory -- or
    dispatched there by the build's own per-module fan-out -- must
    still resolve to its true place in the whole course tree, rather
    than treating that module directory as its own root (which is how
    two modules sharing a same-shaped subpath used to collide in
    Canvas). A path outside the root, or with no root at all, retains
    the old basename-only behaviour."""
    absolute = os.path.abspath(os.fspath(filename))
    root = config.git_root() or os.path.abspath(os.getcwd())
    if os.path.commonpath([root, absolute]) != root:
        return os.path.basename(os.path.normpath(filename))
    return os.path.relpath(absolute, root)


def __canvas_folder_path(filename):
    relative = __course_relative_path(filename)
    parent = os.path.dirname(relative)
    parts = [TENT_POLE_FOLDER]
    if parent:
        parts.extend(parent.split(os.sep))
    return "course files/" + "/".join(parts)


def __parent_folder_path(filename):
    """Canvas upload path beneath the course root."""
    return __canvas_folder_path(filename).removeprefix("course files/")


def __folder_for_path(filename, course):
    """Find the Canvas folder for a local course-relative path."""
    full_path = __canvas_folder_path(filename)
    folders = {folder.full_name: folder for folder in course.get_folders()}
    return folders.get(full_path)


def __find_file(filename, course, folder_id=None):
    local_path = filename
    filename = __canvasfilename_from_path(local_path)
    if folder_id is None:
        folder = __folder_for_path(local_path, course)
        if folder is None:
            return None
        folder_id = folder.id
    for f in course.get_files():
        if f.filename == filename and f.folder_id == folder_id:
            return f

def __data(filename, course):
    canvasfile = __find_file(filename,course)
    if canvasfile is None:
        raise click.ClickException(
            "File {} not found in its managed Canvas folder".format(filename)
        )
    return {
        "hash": manifest.hash_file(filename),
        "size": canvasfile.size,
        "content-type": canvasfile.__dict__["content-type"],
        "id": canvasfile.id,
        "course": course.id,
        "folder_id": canvasfile.folder_id,
        "filename": canvasfile.filename,
        "media_entry_id": canvasfile.media_entry_id
    }

def __tpf_path(filename):
    return filename + ".tpf"

def __load_tpf(filename):
    tpffile = __tpf_path(filename)
    if not os.path.exists(tpffile):
        raise click.ClickException(
            "No {} found -- run push and dump first".format(tpffile)
        )
    with open(tpffile) as fh:
        return toml.load(fh)

def __local_drift(filename, recorded):
    recorded_hash = recorded.get("hash")
    if recorded_hash is None:
        return "no hash recorded in {} -- push and dump again".format(__tpf_path(filename))
    if manifest.hash_file(filename) != recorded_hash:
        return "local file has changed since it was last pushed"
    return None

def __remote_drift(filename, recorded, courseobj, deep=False):
    if "folder_id" in recorded:
        canvasfile = __find_file(filename, courseobj, recorded["folder_id"])
    else:
        ## Recorded before per-path Canvas folders existed, when every
        ## push landed in the single flat TENT_POLE_FOLDER and a file
        ## was matched by name alone, with no folder concept at all --
        ## keep matching the same way for these, rather than
        ## recomputing (and failing to find) a nested path that never
        ## applied to them.
        filename_only = __canvasfilename_from_path(filename)
        canvasfile = next(
            (f for f in courseobj.get_files() if f.filename == filename_only),
            None,
        )
    if canvasfile is None:
        return "file no longer found on Canvas"

    recorded_size = recorded.get("size")
    if recorded_size is not None and canvasfile.size != recorded_size:
        return "remote file size changed since last push (was {}, now {})".format(
            recorded_size, canvasfile.size
        )

    if deep:
        recorded_hash = recorded.get("hash")
        if recorded_hash is not None:
            remote_hash = manifest.hash_bytes(canvasfile.get_contents(binary=True))
            if remote_hash != recorded_hash:
                return "remote file content differs from what was pushed (deep check)"
    return None


## CLI
@click.group()
def file():
    pass

@file.command(help="""Return some information about a file.""")
@click.argument("filename")
def data(filename):
    data = __data(filename, course=course.course_obj())
    print(toml.dumps(data))

@file.command(help="Dump information to a local file.")
@click.argument("filename")
@click.option("--wait", is_flag=True, help="Wait for the file's remote "
              "state to fully resolve before writing the dump, polling "
              "every 2s. Most useful for media, which returns a "
              "placeholder until transcoding finishes.")
def dump(filename, wait):
    courseobj = course.course_obj()
    data = __data(filename, course=courseobj)
    while wait and data.get("media_entry_id") == "maybe":
        time.sleep(2)
        data = __data(filename, course=courseobj)
    with open(filename + ".tpf", "w") as fh:
        toml.dump(data, fh)

@file.command(help="Create or Update a file")
@click.argument("filename")
def push(filename):
    ## on_duplicate="overwrite": Canvas's own upload API defaults to
    ## "rename" when this isn't passed, silently leaving the existing
    ## file untouched and creating a second, differently-named copy
    ## instead -- confirmed against a real course, not assumed.
    ## Overwriting is always correct here specifically because every
    ## push is scoped to the managed folder for this local path: a
    ## same-named collision there is this file's own previous push.
    courseobj = course.course_obj()
    courseobj.upload(
        filename,
        parent_folder_path=__parent_folder_path(filename),
        on_duplicate="overwrite",
    )

@file.command(help="Check whether the local file has changed since it was "
                    "last pushed. Local only, no network access.")
@click.argument("filename")
def check(filename):
    recorded = __load_tpf(filename)
    problem = __local_drift(filename, recorded)
    if problem:
        raise click.ClickException(problem)
    print("OK: {} unchanged since last push".format(filename))

@file.command(help="Check local and remote drift: local changes, and "
                    "whether the remote file's size (or, with --deep, its "
                    "actual content) differs from what was last pushed.")
@click.argument("filename")
@click.option("--deep", is_flag=True, help="Download and hash the remote "
              "file for a byte-exact comparison, instead of just its size.")
def verify(filename, deep):
    recorded = __load_tpf(filename)
    courseobj = course.course_obj()
    problems = [
        p for p in (
            __local_drift(filename, recorded),
            __remote_drift(filename, recorded, courseobj, deep=deep),
        )
        if p
    ]
    if problems:
        raise click.ClickException("; ".join(problems))
    print("OK: {} matches local and remote state".format(filename))
