"""Offline tests for the Java task creator and real compile/run action."""

import shutil

import pytest

from tent_pole.doit_rules import java as java_rules

PANDOC = shutil.which("pandoc")
JAVAC = shutil.which("javac")
JAVA = shutil.which("java")
pytestmark = pytest.mark.skipif(
    PANDOC is None or JAVAC is None or JAVA is None,
    reason="pandoc and a Java toolchain are required",
)


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def course_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_task_out_compiles_and_runs_a_nested_java_include(course_dir):
    source = course_dir / "01-first-version" / "HelloWorld.java"
    _write(
        source,
        "public class HelloWorld {"
        " public static void main(String[] args) {"
        ' System.out.println("Hello, World!");'
        " }"
        "}",
    )
    _write(
        course_dir / "page.md",
        "```{.java include=01-first-version/HelloWorld.java output=true}\n```\n",
    )

    (task,) = list(java_rules.task_java_out())

    assert task["name"] == "01-first-version/HelloWorld.out"
    assert task["file_dep"] == ["01-first-version/HelloWorld.java"]
    assert task["targets"] == ["01-first-version/HelloWorld.out"]
    action, args = task["actions"][0]
    action(*args)

    output = course_dir / "01-first-version" / "HelloWorld.out"
    assert output.read_text().strip() == "Hello, World!"
    assert list((course_dir / "01-first-version").glob("*.class")) == []
