"""doit task-creators mirroring tent_pole/make-rules/python/rules.inc --
capturing a script's output/traceback/REPL-transcript for embedding in
course content. Builds on doit_rules/core.py's own discovery approach:
which .py files need which treatment is read off the same per-page
dependency lists core.py already scans, not off every .py file in the
directory (that would build outputs nothing ever references)."""

import glob
import os
import subprocess

from .. import include_deps_filter

TENT_POLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_SHELL = os.path.join(TENT_POLE_DIR, "bin", "python-shell")


def _referenced(suffix):
    """Every distinct path ending ".<suffix>" that some page's own
    include=/output=/stout=/crash= attributes reference -- mirrors
    CodeIncludeAttrs' own stem+suffix shape, so `os.path.splitext` on
    one of these paths recovers the source .py file directly."""
    seen = set()
    result = []
    for md in glob.glob("*.md"):
        if md.endswith(".quiz.md"):
            continue
        html_deps, full_deps = include_deps_filter.parse(md)
        for dep in html_deps + full_deps:
            if dep.endswith("." + suffix) and dep not in seen:
                seen.add(dep)
                result.append(dep)
    return result


def _run(py, target, mode):
    ## Run python with the same working directory as the python file,
    ## writing to the target's absolute path -- computed before the
    ## cwd change, same as make's own $(abspath $@).
    target_abs = os.path.abspath(target)
    directory = os.path.dirname(py) or "."
    with open(target_abs, "w") as fh:
        if mode == "stdout":
            subprocess.run(["python3", os.path.basename(py)], cwd=directory, stdout=fh, check=True)
            fh.write(" \n")
        elif mode == "stderr":
            ## A crash script is expected to exit non-zero -- mirrors
            ## make's leading "-" on this recipe.
            subprocess.run(["python3", os.path.basename(py)], cwd=directory, stderr=fh)
        elif mode == "shell":
            with open(py) as src:
                subprocess.run([PYTHON_SHELL], cwd=directory, stdin=src, stdout=fh, check=True)
        elif mode == "test":
            ## Non-zero exit (a failing test) is not a build failure --
            ## same tolerance as "stderr" above.
            subprocess.run(["pytest", os.path.basename(py)], cwd=directory, stdout=fh)
            fh.write(" \n")


def task_out():
    """%.out: %.py -- run python, capture stdout."""
    for out in _referenced("out"):
        py = os.path.splitext(out)[0] + ".py"
        yield {
            "name": out,
            "actions": [(_run, [py, out, "stdout"])],
            "file_dep": [py],
            "targets": [out],
        }


def task_crash():
    """%.crash: %.py -- run python, capture stderr; non-zero exit is
    the expected/demonstrated behaviour, not a build failure."""
    for crash in _referenced("crash"):
        py = os.path.splitext(crash)[0] + ".py"
        yield {
            "name": crash,
            "actions": [(_run, [py, crash, "stderr"])],
            "file_dep": [py],
            "targets": [crash],
        }


def task_stout():
    """%.stout: %.py -- feed the file through tent-pole's own
    REPL-transcript tool (bin/python-shell)."""
    for stout in _referenced("stout"):
        py = os.path.splitext(stout)[0] + ".py"
        yield {
            "name": stout,
            "actions": [(_run, [py, stout, "shell"])],
            "file_dep": [py],
            "targets": [stout],
        }


def task_test_out():
    """%.test_out: %.py -- run pytest, capture stdout. Unlike .out/
    .crash/.stout, a page never sets an attribute to ask for this --
    it's always a plain include= directly on the already-derived
    .test_out file itself (there's no "test=true" CodeIncludeAttrs
    flag), but _referenced's own suffix-matching discovery already
    covers that shape."""
    for test_out in _referenced("test_out"):
        py = test_out[: -len(".test_out")] + ".py"
        yield {
            "name": test_out,
            "actions": [(_run, [py, test_out, "test"])],
            "file_dep": [py],
            "targets": [test_out],
        }
