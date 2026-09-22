import canvasapi.exceptions
import click
import dpath
import importlib.resources
import logging
import os
import subprocess
import sys


from . import config
from . import course
from . import file
from . import module
from . import page
from . import quiz


logger = logging.getLogger("canvasapi")
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

##handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
#logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

## CLI Follows
@click.group()
@click.option("-c","--course", "course", help="Course ID")
@click.option("--beta", is_flag=True, help="Target [dev] test_course_id/"
              "test_api_url/test_api_key from your config instead of "
              "[general]/[course], for this invocation only. Takes "
              "priority over -c/--course.")
def main(course, beta):
    if beta:
        os.environ["TENT_POLE_USE_TEST_CONFIG"] = "1"
    if course:
        dpath.new(config.CONFIG, "course/identifier", "temp")
        dpath.set(config.CONFIG, "course/identifier", course[1:])

@main.command(name="pkg-dir", help="Print the path to tent-pole's "
              "installed package directory, e.g. for a downstream "
              "Makefile to locate the shipped make-rules/ and bin/.")
def pkg_dir():
    print(os.path.dirname(__file__))

def __init_template(name):
    """Raw text of tent_pole/init-template/<name> -- the source for
    everything `tent-pole init` writes, kept as real files rather than
    Python string literals so they're easy to read and edit directly."""
    return importlib.resources.files("tent_pole").joinpath(
        "init-template", name
    ).read_text()

def __write_if_absent(path, content):
    if os.path.exists(path):
        print("{} already exists, skipping".format(path))
        return
    with open(path, "w") as f:
        f.write(content)
    print("Created {}".format(path))

def __git_init_unless_already_in_repo():
    try:
        inside_repo = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True,
        ).returncode == 0
    except FileNotFoundError:
        raise click.ClickException("git not found on PATH")

    if inside_repo:
        print("Already inside a git repository, skipping git init")
    else:
        subprocess.run(["git", "init"], check=True)

@main.command(help="Scaffold a new tent-pole project in the current "
              "directory: git init, a bootstrap Makefile, a starter "
              "tent-pole.toml, and hello.md. Safe to re-run -- never "
              "overwrites a file that's already there.")
@click.option("--no-git", is_flag=True, help="Don't run git init.")
def init(no_git):
    if not no_git:
        __git_init_unless_already_in_repo()

    __write_if_absent("Makefile", __init_template("Makefile"))
    __write_if_absent("tent-pole.toml", __init_template("tent-pole.toml"))
    __write_if_absent("hello.md", __init_template("hello.md"))

main.add_command(config.config)
main.add_command(course.course)
main.add_command(file.file)
main.add_command(module.module)
main.add_command(page.page)
main.add_command(quiz.quiz)

def cli():
    """Console-script entry point (see pyproject.toml) -- Click's own
    dispatch only catches ClickException/Abort, so an uncaught
    CanvasException from inside a command would otherwise surface as a
    raw traceback ending in canvasapi's own generic message, which
    keeps only the status code and discards the actual response body
    and headers entirely. The response itself is still sitting in the
    Requester's own cache regardless -- see config.last_response.

    Only enriches the *generic* CanvasException (the literal base
    class, not a named subclass like BadRequest/Forbidden/etc) --
    those already build their own message from response.text, so
    appending it again would just be a duplicate."""
    try:
        main()
    except canvasapi.exceptions.CanvasException as e:
        if type(e) is canvasapi.exceptions.CanvasException:
            response = config.last_response()
            if response is not None:
                click.echo("Error: {}\nCanvas said: {}".format(e, response.text), err=True)
                sys.exit(1)
        click.echo("Error: {}".format(e), err=True)
        sys.exit(1)
