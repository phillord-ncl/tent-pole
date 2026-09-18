import canvasapi.exceptions
import click
import dpath.util
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
        dpath.util.new(config.CONFIG, "course/identifier", "temp")
        dpath.util.set(config.CONFIG, "course/identifier", course[1:])

@main.command(name="pkg-dir", help="Print the path to tent-pole's "
              "installed package directory, e.g. for a downstream "
              "Makefile to locate the shipped make-rules/ and bin/.")
def pkg_dir():
    print(os.path.dirname(__file__))

INIT_DEV_WRAPPER_DIR = "dev-scripts"
INIT_DEV_WRAPPER_IMPL = "tent-pole-dev.sh"
INIT_DEV_MK = "dev.mk"

def __init_template(name):
    """Raw text of tent_pole/init-template/<name> -- the source for
    everything `tent-pole init` writes, kept as real files rather than
    Python string literals so they're easy to read and edit directly.
    Only the Makefile/tent-pole-dev.sh/dev.mk templates have {ph}
    placeholders for callers to .format(); tent-pole.toml/hello.md
    have none (and tent-pole.toml's own {id="hello"} would collide
    with .format() if it tried)."""
    return importlib.resources.files("tent_pole").joinpath(
        "init-template", name
    ).read_text()

def __checkout_root():
    """The directory containing tent-pole's own pyproject.toml -- one
    level up from pkg-dir (tent_pole/main.py's own package
    directory)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def __write_if_absent(path, content):
    if os.path.exists(path):
        print("{} already exists, skipping".format(path))
        return
    with open(path, "w") as f:
        f.write(content)
    print("Created {}".format(path))

def __symlink_if_absent(path, target):
    if os.path.lexists(path):
        print("{} already exists, skipping".format(path))
        return
    os.symlink(target, path)
    print("Created {} -> {}".format(path, target))

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

def __write_dev_wrappers():
    """Writes dev-scripts/tent-pole-dev.sh (the one real script, picking
    the tool to run from $1 or from its own invoked name) plus a
    symlink per pandoc filter rules.inc can be pointed at, and
    dev-scripts/dev.mk overriding TENT_POLE/CANVAS_FILTER/
    CODE_INCLUDE_FILTER/INCLUDE_DEPS_FILTER to use them -- for a
    project that lives anywhere, not just below the tent-pole checkout
    itself."""
    checkout = __checkout_root()
    if not os.path.exists(os.path.join(checkout, "pyproject.toml")):
        raise click.ClickException(
            "--tent-pole-dev needs a Poetry checkout -- no pyproject.toml "
            "found at {} (this tent-pole doesn't look like it's running "
            "from one, e.g. it's a pipx/pip install)".format(checkout)
        )

    os.makedirs(INIT_DEV_WRAPPER_DIR, exist_ok=True)
    impl_name = os.path.splitext(INIT_DEV_WRAPPER_IMPL)[0]
    impl = os.path.join(INIT_DEV_WRAPPER_DIR, INIT_DEV_WRAPPER_IMPL)
    __write_if_absent(impl, __init_template(INIT_DEV_WRAPPER_IMPL).format(
        checkout=checkout, impl_name=impl_name,
    ))
    os.chmod(impl, 0o755)

    for tool in ["canvas-filter", "code-include-filter", "include-deps-filter"]:
        __symlink_if_absent(
            os.path.join(INIT_DEV_WRAPPER_DIR, "{}.sh".format(tool)),
            INIT_DEV_WRAPPER_IMPL,
        )

    __write_if_absent(
        os.path.join(INIT_DEV_WRAPPER_DIR, INIT_DEV_MK),
        __init_template(INIT_DEV_MK).format(
            dir=INIT_DEV_WRAPPER_DIR, impl=INIT_DEV_WRAPPER_IMPL,
        ),
    )

def __makefile_content(tent_pole_dev):
    prelude = ""
    if tent_pole_dev:
        __write_dev_wrappers()
        prelude = "-include {}/{}\n\n".format(INIT_DEV_WRAPPER_DIR, INIT_DEV_MK)
    return __init_template("Makefile").format(prelude=prelude)

@main.command(help="Scaffold a new tent-pole project in the current "
              "directory: git init, a bootstrap Makefile, a starter "
              "tent-pole.toml, and hello.md. Safe to re-run -- never "
              "overwrites a file that's already there.")
@click.option("--no-git", is_flag=True, help="Don't run git init.")
@click.option("--tent-pole-dev", is_flag=True, help="Add -include "
              "dev-scripts/dev.mk to the Makefile, and write it plus "
              "a wrapper script (dev-scripts/tent-pole-dev.sh, plus a "
              "symlink per pandoc filter) that run tent-pole and its "
              "filters from this tent-pole's own checkout via Poetry, "
              "instead of an installed copy -- for developing "
              "tent-pole itself, from a project that lives anywhere.")
def init(no_git, tent_pole_dev):
    if not no_git:
        __git_init_unless_already_in_repo()

    __write_if_absent("Makefile", __makefile_content(tent_pole_dev))
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
