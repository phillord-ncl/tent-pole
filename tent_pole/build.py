import glob
import sys
import os

import click
from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain

from . import doit_rules
from . import include_deps_filter
from .doit_rules.generate_makefile import _kind as _script_kind

## Longest/most-specific first, so a multi-part suffix (.quiz.full.html)
## isn't mistaken for a shorter one it also ends with (.html) -- used
## only to recognise an already-fully-qualified name so it's left
## alone, never to guess a stem from an arbitrary target.
_KNOWN_SUFFIXES = (
    ".quiz.full.html", ".full.html", "_slidy.html", "_book.html", "_web.html",
    ".html", ".pdf", ".tpp", ".tpq", ".tpf", ".test_out", ".out", ".crash", ".stout",
)


def _referenced_py_by_basename(stem):
    """A .py path (relative to cwd, possibly in a different directory
    entirely -- e.g. "../python/hello_world.py") that some page in cwd
    references via include=, whose own basename-without-".py" matches
    stem -- the same discovery task_out/task_tpf already do, reused
    here so a bare name resolves correctly even when the script it
    names doesn't live in the current directory itself."""
    for md in glob.glob("*.md"):
        if md.endswith(".quiz.md"):
            continue
        html_deps, full_deps = include_deps_filter.parse(md)
        for dep in html_deps + full_deps:
            if dep.endswith(".py") and os.path.basename(dep)[:-3] == stem:
                return dep
    return None


def _resolve_bare_name(name):
    """"programming" -> "programming.tpp" (a page), "foo" -> "foo.tpq"
    (a quiz), "hello_world" -> "hello_world.out"/".crash"/".stout" (a
    script, via the same content-sniffing rule generate_makefile.py's
    own port uses, checked both directly in cwd and, failing that,
    among this directory's own referenced scripts wherever they
    actually live) -- so a caller can name a source file's own stem
    without needing to already know tent-pole's internal stamp-file
    naming convention, or which directory a referenced script lives in.
    Left alone if the name already ends in one of tent-pole's own
    suffixes (checked first, deliberately: "already exists on disk"
    alone isn't a safe test here -- an already-pushed "foo.tpp"
    existing as a real file must not be re-treated as a raw asset
    needing its own "foo.tpp.tpf"), or if it matches no known source
    pattern at all -- either way, doit reports its own error if the
    result isn't a real task."""
    if name.endswith(_KNOWN_SUFFIXES):
        return name
    if os.path.exists(name + ".quiz.md"):
        return name + ".tpq"
    if os.path.exists(name + ".md"):
        return name + ".tpp"
    if os.path.exists(name + ".py"):
        suffix, _mode = _script_kind(name + ".py")
        return name + "." + suffix
    referenced_py = _referenced_py_by_basename(name)
    if referenced_py:
        suffix, _mode = _script_kind(referenced_py)
        return referenced_py[:-3] + "." + suffix
    if os.path.exists(name):
        return name + ".tpf"
    return name


def _resolve_argv(argv):
    return [
        arg if arg.startswith("-") or "=" in arg or ":" in arg
        else _resolve_bare_name(arg)
        for arg in argv
    ]


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
    return main.run(_resolve_argv(argv))


@click.command(
    name="build",
    context_settings={"ignore_unknown_options": True},
    help="Build this directory (and its own child module directories) "
         "with doit, tent-pole's make replacement. Everything after "
         "`build` is passed straight through to doit itself -- a task "
         "name, a target file path (e.g. `introduction.tpp`), or just a "
         "source file's own stem (e.g. `introduction`, resolved to "
         "introduction.tpp/.tpq/.out/.crash/.stout/.tpf as appropriate) "
         "-- plus -n/-j/list/etc; with nothing given, doit's own "
         "default_tasks (\"pages\") runs.",
)
@click.argument("doit_args", nargs=-1, type=click.UNPROCESSED)
def build(doit_args):
    sys.exit(run_build(doit_args))
