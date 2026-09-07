import click
import os
import toml

from . import course
from . import manifest

## Fixed, not configurable -- every file tent-pole uploads lands here,
## rather than Canvas's generic default "unfiled" folder, so "did
## tent-pole manage this" becomes a cheap folder_id check. Must only ever
## be passed as upload()'s parent_folder_path -- never via a separate
## create_folder() call, which resolves relative to a different parent
## ("unfiled" rather than the course root) and creates a second,
## inconsistent folder of the same name.
TENT_POLE_FOLDER = "tent-pole"

def __canvasfilename_from_path(path):
    return os.path.basename(path)

def __find_file(filename, course):
    filename =__canvasfilename_from_path(filename)
    for f in course.get_files():
        if f.filename == filename:
            return f

def __data(filename, course):
    canvasfile = __find_file(filename,course)
    return {
        "hash": manifest.hash_file(filename),
        "size": canvasfile.size,
        "content-type": canvasfile.__dict__["content-type"],
        "id": canvasfile.id,
        "course": course.id,
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
    canvasfile = __find_file(filename, courseobj)
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
def dump(filename):
    with open(filename + ".tpf", "w") as fh:
        toml.dump(__data(filename, course=course.course_obj()),fh)

@file.command(help="Create or Update a file")
@click.argument("filename")
def push(filename):
    course.course_obj().upload(filename, parent_folder_path=TENT_POLE_FOLDER)

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
