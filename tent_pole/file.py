import click
import os
import toml

from . import config

def __canvasfilename_from_path(path):
    return os.path.basename(path)

def __find_file(filename, course):
    filename =__canvasfilename_from_path(filename)
    for f in course.get_files():
        if f.filename == filename:
            return f

## CLI
@click.group()
def file():
    pass

@file.command(help="""Return some information about a file.""")
@click.argument("filename")
def data(filename):
    course=config.config_course_obj()
    canvasfile = __find_file(filename,course)
    data = {
        "uuid": canvasfile.uuid,
        "content-type": canvasfile.__dict__["content-type"],
        "id": canvasfile.id,
        "course": course.id,
        "filename": canvasfile.filename,
    }
    print(toml.dumps(data))


@file.command(help="Create or Update a file")
@click.argument("filename")
def push(filename):
    course = config.config_canvas().get_course(config.config_course())
    course.upload(filename)


##  "id": 3156340,
