import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CodeIncludeAttrs:
    """The include=/output=/stout=/crash= attributes on a CodeBlock,
    shared by canvas_filter, code_include_filter, and
    include_deps_filter -- all three need the same parsing and the
    same derived .out/.stout/.crash path shape."""
    include: Optional[str]
    output: bool
    stout: bool
    crash: bool

    @classmethod
    def from_element(cls, elem):
        return cls(
            include=elem.attributes.get("include"),
            output=bool(elem.attributes.get("output")),
            stout=bool(elem.attributes.get("stout")),
            crash=bool(elem.attributes.get("crash")),
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
