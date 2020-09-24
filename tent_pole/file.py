import click
import os
import toml

from . import course

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
        "uuid": canvasfile.uuid,
        "content-type": canvasfile.__dict__["content-type"],
        "id": canvasfile.id,
        "course": course.id,
        "filename": canvasfile.filename,
        "media_entry_id": canvasfile.media_entry_id
    }


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
    course.course_obj().upload(filename)


