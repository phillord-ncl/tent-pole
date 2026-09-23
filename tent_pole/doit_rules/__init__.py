"""tent-pole's built-in doit task set -- the doit equivalent of a leaf
Makefile that does `include $(TENT_POLE_DIR)/make-rules/rules.inc` /
`.../python/rules.inc` and then defines its own `pages`/`quizzes`/
`full` goals with a recursive fan-out to child module directories
(course_import.py's ROOT_MAKEFILE_TEMPLATE, today). `tent-pole build`
loads this module directly when no local dodo.py exists (see
tent_pole/build.py); a course that needs extra rules of its own (e.g.
CSC1034's lecture-slide pandoc pipeline in make-inc/rules.inc) adds a
real dodo.py doing `from tent_pole.doit_rules import *` to get
everything here, then defines its own extra task_* functions alongside.

task_pages/task_quizzes/task_full are deliberately NOT the same names
as core.py's own task_page_push/task_quiz_push/task_full_html: doit
would otherwise register the same target file under two different
task names (one from core's own name, one from re-exporting it here),
which doit treats as an error. Combining them via `yield from` under a
new name avoids that -- see each function below.
"""

import glob
import os
import subprocess
import sys

from . import core
from .core import task_html, task_quiz_full, task_tpf, task_reorder  # noqa: F401
from .python import task_out, task_crash, task_stout  # noqa: F401

## See core.py's own note: resolves to whichever tent-pole launched
## this process, not a hardcoded name.
TENT_POLE = os.environ.get("TENT_POLE") or sys.argv[0]


def _fan_out(goal):
    """One subtask per immediate child module directory, unconditionally
    dispatching `tent-pole build <goal>` with that directory as cwd --
    same shape as `for d in $(SUBDIRS); do $(MAKE) -C $$d <goal>; done`,
    except SUBDIRS is discovered by a one-level glob here instead of
    baked into a generated Makefile string. No file_dep/targets on
    these tasks: doit treats a task with neither as always stale, so
    the dispatch is unconditional for free, same as make's own loop
    runs every time regardless of whether that child needs anything."""
    for child_toml in glob.glob("*/tent-pole.toml"):
        moddir = os.path.dirname(child_toml)
        yield {
            "name": moddir,
            "actions": [(subprocess.run, [[TENT_POLE, "build", goal]],
                         {"cwd": moddir, "check": True})],
        }


def task_pages():
    """pages: $(MD_SOURCES:%.md=%.tpp), plus fan-out -- tent-pole
    build's default goal."""
    yield from core.task_page_push()
    yield from _fan_out("pages")


def task_quizzes():
    """quizzes: $(QUIZ_SOURCES:%.quiz.md=%.tpq), plus fan-out."""
    yield from core.task_quiz_push()
    yield from _fan_out("quizzes")


def task_full():
    """full: $(MD_SOURCES:%.md=%.full.html), plus fan-out -- no Canvas
    access at all, matching make's own "full" goal."""
    yield from core.task_full_html()
    yield from _fan_out("full")


DOIT_CONFIG = {"default_tasks": ["pages"]}
