import sys
import os

import click
from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain

from . import doit_rules


def run_build(argv):
    """Run doit against a local ./dodo.py if one exists -- full doit
    semantics, in-process -- so an author's own extra task_*
    functions (e.g. CSC1034's lecture-slide pandoc pipeline in
    make-inc/rules.inc) just work. Falls back to tent-pole's own
    built-in rules (tent_pole.doit_rules) when no dodo.py exists,
    which is the common case (most module directories need no
    customisation at all). Either way this runs inside tent-pole's
    own interpreter, never a separately invoked `doit` -- so
    `from tent_pole.doit_rules... import ...` inside a dodo.py can
    never fail to resolve against the wrong installed environment."""
    ## A course repo's own directory tree is content to look at and
    ## edit, not a Python package -- a __pycache__ next to every
    ## dodo.py (and next to any course-level module it imports, e.g.
    ## make-inc/doit_rules.py) is pure clutter nobody asked for.
    sys.dont_write_bytecode = True
    if os.path.exists("dodo.py"):
        main = DoitMain()
    else:
        main = DoitMain(ModuleTaskLoader(doit_rules))
    return main.run(list(argv))


@click.command(
    name="build",
    context_settings={"ignore_unknown_options": True},
    help="Build this directory (and its own child module directories) "
         "with doit, tent-pole's make replacement. Everything after "
         "`build` is passed straight through to doit itself -- a task "
         "name, a target file path (e.g. `introduction.tpp`), -n/-j/"
         "list/etc; with nothing given, doit's own default_tasks "
         "(\"pages\") runs.",
)
@click.argument("doit_args", nargs=-1, type=click.UNPROCESSED)
def build(doit_args):
    sys.exit(run_build(doit_args))
