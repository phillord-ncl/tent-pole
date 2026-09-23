"""doit task-creators mirroring tent_pole/make-rules/rules.inc -- the
generic, project-type-agnostic rules any tent-pole project uses,
Python or not. See doit_rules/python.py for the Python-specific layer,
and doit_rules/__init__.py for the pages/quizzes/full goals a course
actually builds (this module's rules are the building blocks, not
those goals themselves -- see its own docstring for why the two are
kept apart).

v1 note: dependency discovery (which files a page embeds/includes) is
computed eagerly here, by reparsing each page's markdown via pandoc on
every doit invocation, rather than via a cached calc_dep task backed by
its own file_dep. That costs one extra pandoc parse per page per build
even when nothing changed -- unlike make's %.tpd, which skips
regenerating on an unchanged page -- but correctness is unaffected:
only the parse is repeated, never a page/file push, since the actual
push tasks below still have their own file_dep-based up-to-date
checks. A calc_dep-based version is a follow-up, not a prerequisite for
this to be correct. See claude-make-replacement.md.
"""

import glob
import os
import subprocess
import sys

from .. import include_deps_filter

## Not a hardcoded "tent-pole": subprocess actions below (fan-out,
## page/file push, module create/reorder) call back into tent-pole
## itself, so they must resolve to whichever tent-pole actually
## launched this process (e.g. a suffixed pipx install like
## tent-pole-next) rather than to a different tent-pole that happens
## to be first on PATH. sys.argv[0] is that exact binary -- a bare-name
## invocation is already resolved to a full path by the shell before
## Python ever sees it.
TENT_POLE = os.environ.get("TENT_POLE") or sys.argv[0]
CANVAS_FILTER = os.environ.get("CANVAS_FILTER", "canvas-filter")
CODE_INCLUDE_FILTER = os.environ.get("CODE_INCLUDE_FILTER", "code-include-filter")


def _md_sources():
    return [md for md in glob.glob("*.md") if not md.endswith(".quiz.md")]


def _quiz_sources():
    return glob.glob("*.quiz.md")


def task_html():
    """%.html: %.md -- pandoc through canvas-filter."""
    for md in _md_sources():
        html = md[:-3] + ".html"
        html_deps, _ = include_deps_filter.parse(md)
        yield {
            "name": html,
            "actions": [["pandoc", "--filter=" + CANVAS_FILTER, md, "-o", html]],
            "file_dep": [md] + html_deps,
            "targets": [html],
            "clean": True,
        }


def task_full_html():
    """%.full.html: %.md -- pandoc through code-include-filter, no
    Canvas access at all. Not exposed as a top-level "full" goal
    itself -- see doit_rules/__init__.py's task_full, which also fans
    out to child module directories."""
    for md in _md_sources():
        full = md[:-3] + ".full.html"
        _, full_deps = include_deps_filter.parse(md)
        yield {
            "name": full,
            "actions": [[
                "pandoc", "--embed-resources", "--standalone",
                "--filter=" + CODE_INCLUDE_FILTER, md, "-o", full,
            ]],
            "file_dep": [md] + full_deps,
            "targets": [full],
            "clean": True,
        }


def task_quiz_full():
    """%.quiz.full.html: %.quiz.md -- same recipe as %.full.html;
    plain pandoc already renders a quiz's headers/checkboxes/code
    correctly for a human preview."""
    for qmd in _quiz_sources():
        full = qmd[: -len(".quiz.md")] + ".quiz.full.html"
        yield {
            "name": full,
            "actions": [[
                "pandoc", "--embed-resources", "--standalone",
                "--filter=" + CODE_INCLUDE_FILTER, qmd, "-o", full,
            ]],
            "file_dep": [qmd],
            "targets": [full],
            "clean": True,
        }


def task_page_push():
    """%.tpp: %.html -- page push (which now records its own local
    push-tracking state as part of the same push, same as quiz push
    already does -- see page.py's push/__record_push). Not exposed as
    a top-level "pages" goal itself -- see doit_rules/__init__.py's
    task_pages."""
    for md in _md_sources():
        html = md[:-3] + ".html"
        tpp = md[:-3] + ".tpp"
        yield {
            "name": tpp,
            "actions": [
                [TENT_POLE, "page", "push", html],
            ],
            "file_dep": [html],
            "targets": [tpp],
            "clean": True,
        }


def task_quiz_push():
    """%.tpq: %.quiz.md -- quiz push (push already both creates-or-
    updates and writes its own stamp, so there is no separate dump
    step, unlike a page). Not exposed as a top-level "quizzes" goal
    itself -- see doit_rules/__init__.py's task_quizzes."""
    for qmd in _quiz_sources():
        tpq = qmd[: -len(".quiz.md")] + ".tpq"
        yield {
            "name": tpq,
            "actions": [[TENT_POLE, "quiz", "push", qmd]],
            "file_dep": [qmd],
            "targets": [tpq],
            "clean": True,
        }


def task_tpf():
    """%.tpf: % / %.mp4.tpf: %.mp4 -- push (+dump) any local file a
    page embeds or links to. The set of files is discovered the same
    way as task_html's own file_dep, by scanning every page's
    dependency list rather than being told about them directly (doit
    has no equivalent of make's implicit pattern-rule dispatch for a
    dynamically-discovered target)."""
    seen = set()
    for md in _md_sources():
        html_deps, _ = include_deps_filter.parse(md)
        for dep in html_deps:
            if not dep.endswith(".tpf") or dep in seen:
                continue
            seen.add(dep)
            raw = dep[: -len(".tpf")]
            ## Media needs --wait: Canvas returns a placeholder
            ## media_entry_id until transcoding finishes, and
            ## canvas_filter's own mp4 handling needs the real one.
            dump_action = (
                [TENT_POLE, "file", "dump", "--wait", raw] if raw.endswith(".mp4")
                else [TENT_POLE, "file", "dump", raw]
            )
            yield {
                "name": raw,
                "actions": [[TENT_POLE, "file", "push", raw], dump_action],
                "file_dep": [raw],
                "targets": [dep],
                "clean": True,
            }


def _dump_module():
    with open("tent-pole.toml.tpm", "w") as fh:
        subprocess.run([TENT_POLE, "module", "dump"], stdout=fh, check=True)


def task_reorder():
    """tent-pole.toml.tpm: tent-pole.toml -- module reorder (get-or-
    create, safe to run every time) + dump. No separate create step,
    same as the make rule this mirrors."""
    if not os.path.exists("tent-pole.toml"):
        return
    yield {
        "name": "reorder",
        "actions": [[TENT_POLE, "module", "reorder"], (_dump_module, [])],
        "file_dep": ["tent-pole.toml"],
        "targets": ["tent-pole.toml.tpm"],
        "clean": True,
    }
