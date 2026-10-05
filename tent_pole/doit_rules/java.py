import glob
import os
import subprocess
import tempfile

from .. import include_deps_filter


def _referenced(suffix):
    """Return distinct generated files with the requested suffix."""
    seen = set()
    result = []
    for markdown in glob.glob("*.md"):
        if markdown.endswith(".quiz.md"):
            continue
        html_deps, full_deps = include_deps_filter.parse(markdown)
        for dependency in html_deps + full_deps:
            if dependency.endswith("." + suffix) and dependency not in seen:
                seen.add(dependency)
                result.append(dependency)
    return result


def _run_java(source, target):
    """Compile and run a default-package Java class, capturing stdout."""
    target_abs = os.path.abspath(target)
    source_dir = os.path.dirname(source) or "."
    source_name = os.path.basename(source)
    class_name = os.path.splitext(source_name)[0]

    with tempfile.TemporaryDirectory() as class_dir:
        subprocess.run(
            ["javac", "-d", class_dir, source_name],
            cwd=source_dir,
            check=True,
        )
        with open(target_abs, "w") as output:
            subprocess.run(
                ["java", "-cp", class_dir, class_name],
                cwd=source_dir,
                stdout=output,
                check=True,
            )
            output.write(" \n")


def task_java_out():
    """Create compile-and-run tasks for referenced Java output files."""
    for output in _referenced("out"):
        source = os.path.splitext(output)[0] + ".java"
        if not os.path.exists(source):
            continue
        yield {
            "name": output,
            "actions": [(_run_java, [source, output])],
            "file_dep": [source],
            "targets": [output],
            "clean": True,
        }
