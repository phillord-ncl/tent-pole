import glob
import io
import os
import subprocess
import tempfile

from panflute import CodeBlock, load

from .. import include_deps_filter
from ..code_include_attrs import CodeIncludeAttrs


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


def _run_java_failure(source, target, compile_fail):
    """Capture an expected Java compilation or runtime failure."""
    target_abs = os.path.abspath(target)
    source_dir = os.path.dirname(source) or "."
    source_name = os.path.basename(source)
    class_name = os.path.splitext(source_name)[0]

    with tempfile.TemporaryDirectory() as class_dir:
        with open(target_abs, "w") as output:
            compile_result = subprocess.run(
                ["javac", "-d", class_dir, source_name],
                cwd=source_dir,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            if compile_fail:
                if compile_result.returncode == 0:
                    os.remove(target_abs)
                    raise RuntimeError(
                        "Expected javac to reject {}".format(source)
                    )
                return
            if compile_result.returncode != 0:
                os.remove(target_abs)
                raise RuntimeError(
                    "Expected {} to compile and crash at runtime, but it "
                    "failed to compile instead".format(source)
                )
            run_result = subprocess.run(
                ["java", "-cp", class_dir, class_name],
                cwd=source_dir,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            if run_result.returncode == 0:
                os.remove(target_abs)
                raise RuntimeError(
                    "Expected Java program {} to fail".format(source)
                )


def _java_failure_targets():
    """Return each Java crash artifact and whether compilation itself
    must fail, rejecting contradictory declarations of one target."""
    targets = {}

    def visit(elem, doc):
        if isinstance(elem, CodeBlock):
            attrs = CodeIncludeAttrs.from_element(elem)
            if attrs.include and attrs.include.endswith(".java"):
                if attrs.compile_fail or attrs.crash:
                    mode = "compile" if attrs.compile_fail else "runtime"
                    previous = targets.get(attrs.crash_path)
                    if previous is not None and previous != mode:
                        raise ValueError(
                            "Conflicting Java failure attributes for {}".format(
                                attrs.crash_path
                            )
                        )
                    targets[attrs.crash_path] = mode
        return elem

    for markdown in glob.glob("*.md"):
        if markdown.endswith(".quiz.md"):
            continue
        result = subprocess.run(
            ["pandoc", "-t", "json", markdown],
            capture_output=True,
            check=True,
            text=True,
        )
        load(io.StringIO(result.stdout)).walk(visit)
    return targets


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


def task_java_crash():
    """Create compile- or runtime-failure tasks for referenced Java crashes."""
    for crash, mode in _java_failure_targets().items():
        source = os.path.splitext(crash)[0] + ".java"
        if not os.path.exists(source):
            continue
        yield {
            "name": crash,
            "actions": [(_run_java_failure, [source, crash, mode == "compile"])],
            "file_dep": [source],
            "targets": [crash],
            "clean": True,
        }
