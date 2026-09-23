"""Doit port of tent_pole/bin/generate_makefile.py -- the dev-only
"run every script in this directory and see what happens" sweep a
leaf's own Makefile-generated used, as opposed to python.py's own
markdown-reference-driven discovery (which only builds outputs a
page's own include=/output=/stout=/crash= attributes actually ask
for). Decides a script's treatment the same way the original tool
does: a name starting "test_" gets pytest'd, "## Status: Crash"/
"## Status: Shell" in its own source picks crash/stout, anything else
gets plain stdout capture; a bare *.pys gets fed through the same
REPL-transcript tool as *.stout.

generate_makefile.py's own glob.glob("*.py") has no exclusion at all,
so it would happily try to run dodo.py itself as if it were demo
content. EXCLUDE exists specifically to make that impossible here --
see the doit-backend port's own note on this exact question.
"""

import glob
import os

from .python import _run

EXCLUDE = {"dodo.py"}


def _kind(path):
    if os.path.basename(path).startswith("test_"):
        return "test_out", "test"
    with open(path) as fh:
        content = fh.read()
    if "## Status: Crash" in content:
        return "crash", "stderr"
    if "## Status: Shell" in content:
        return "stout", "shell"
    return "out", "stdout"


def task_generated():
    """Every *.py's own .out/.crash/.stout/.test_out, and every *.pys'
    own .stout, run unconditionally regardless of whether any page
    references them -- dodo.py (and anything else in EXCLUDE) is
    never a candidate."""
    for src in glob.glob("*.py"):
        if os.path.basename(src) in EXCLUDE:
            continue
        suffix, mode = _kind(src)
        target = src[:-3] + "." + suffix
        yield {
            "name": target,
            "actions": [(_run, [src, target, mode])],
            "file_dep": [src],
            "targets": [target],
        }

    for src in glob.glob("*.pys"):
        target = src[:-4] + ".stout"
        yield {
            "name": target,
            "actions": [(_run, [src, target, "shell"])],
            "file_dep": [src],
            "targets": [target],
        }
