import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CodeIncludeAttrs:
    """The include=/output=/stout=/crash=/hide_crash= attributes on a
    CodeBlock, shared by canvas_filter, code_include_filter, and
    include_deps_filter -- all three need the same parsing and the
    same derived .out/.stout/.crash path shape.

    crash= and hide_crash= are deliberately separate: crash= means
    "this program is expected to crash, build its .crash artifact
    rather than treating a non-zero exit as a build failure" -- a
    build-level declaration that a real "will this code crash?" quiz
    question still needs, but rendering the traceback right there in
    the question answers it for free (tent-pole issue #14 review).
    hide_crash= controls only whether code_filter renders that
    traceback; it does nothing without crash= also being set."""
    include: Optional[str]
    output: bool
    stout: bool
    crash: bool
    hide_crash: bool

    @classmethod
    def from_element(cls, elem):
        return cls(
            include=elem.attributes.get("include"),
            output=bool(elem.attributes.get("output")),
            stout=bool(elem.attributes.get("stout")),
            crash=bool(elem.attributes.get("crash")),
            hide_crash=bool(elem.attributes.get("hide_crash")),
        )

    @property
    def stem(self):
        return os.path.splitext(self.include)[0]

    @property
    def output_path(self):
        return self.stem + ".out"

    @property
    def stout_path(self):
        return self.stem + ".stout"

    @property
    def crash_path(self):
        return self.stem + ".crash"

    def referenced_paths(self):
        """Every file this directive touches."""
        paths = [self.include] if self.include else []
        if self.output:
            paths.append(self.output_path)
        if self.stout:
            paths.append(self.stout_path)
        if self.crash:
            paths.append(self.crash_path)
        return paths
