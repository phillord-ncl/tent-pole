import importlib.resources
import os
import subprocess

import click


def init_template(name):
    """Raw text of tent_pole/init-template/<name> -- the source for
    everything `tent-pole init`/`tent-pole clone` write, kept as real
    files rather than Python string literals so they're easy to read
    and edit directly."""
    return importlib.resources.files("tent_pole").joinpath(
        "init-template", name
    ).read_text()


def write_if_absent(path, content):
    if os.path.exists(path):
        print("{} already exists, skipping".format(path))
        return
    with open(path, "w") as f:
        f.write(content)
    print("Created {}".format(path))


def git_init_unless_already_in_repo():
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
