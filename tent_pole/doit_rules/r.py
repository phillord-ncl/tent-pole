"""doit task-creator for R support -- one task per .R file, running
tent_pole/bin/r-chunks once to produce every chunk's own
output/stout/crash/plot artifacts. Discovery can't mirror
doit_rules/python.py's own _referenced(suffix) shape: a chunk-aware
target like demo_summary-stats.out can't be reversed back to demo.R
by string-splitting the way python.py's whole-file naming allowed --
the chunk name is embedded in the stem, and chunk names can contain
anything. So discovery here walks each page's own CodeBlocks directly
(the same computation include_deps_filter.py's collect_deps() does),
grouping targets by that CodeBlock's own attrs.include instead."""

import glob
import io
import os
import subprocess

from panflute import CodeBlock, load

from ..code_include_attrs import CodeIncludeAttrs

TENT_POLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R_CHUNKS = os.path.join(TENT_POLE_DIR, "bin", "r-chunks")


def _referenced_by_source():
    """{r_source_path: [target_paths...]}, insertion-ordered and
    deduplicated, for every output=/stout=/crash=/plot= some page
    actually references against some .R file."""
    sources = {}

    def visit(elem, doc):
        if isinstance(elem, CodeBlock):
            attrs = CodeIncludeAttrs.from_element(elem)
            if attrs.include and attrs.include.endswith(".R"):
                targets = sources.setdefault(attrs.include, [])
                for wanted, path in (
                    (attrs.output, attrs.output_path),
                    (attrs.stout, attrs.stout_path),
                    (attrs.crash, attrs.crash_path),
                    (attrs.plot, attrs.plot_path),
                ):
                    if wanted and path not in targets:
                        targets.append(path)
        return elem

    for md in glob.glob("*.md"):
        if md.endswith(".quiz.md"):
            continue
        result = subprocess.run(
            ["pandoc", "-t", "json", md],
            capture_output=True, check=True, text=True,
        )
        load(io.StringIO(result.stdout)).walk(visit)

    return sources


def _run(r_file):
    subprocess.run(["Rscript", R_CHUNKS, r_file], check=True)
    return True


def task_r():
    """One task per .R file referenced by some page's output=/stout=/
    crash=/plot=, targets= every distinct path requested anywhere for
    it. A single multi-target task, not one task per target -- doit
    does not merge separately-declared single-target tasks sharing a
    file_dep itself (confirmed directly, see r_support_design.md), so
    this grouping has to be deliberate."""
    for r_file, targets in _referenced_by_source().items():
        if not targets:
            ## A plain include= with no output=/stout=/crash=/plot= at
            ## all needs nothing beyond the .R file itself, already a
            ## checked-in build dependency -- no reason to run r-chunks.
            continue
        yield {
            "name": r_file,
            "actions": [(_run, [r_file])],
            "file_dep": [r_file],
            "targets": targets,
            "clean": True,
        }
