import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CodeIncludeAttrs:
    """The include=/output=/stout=/crash=/compile-fail=/hide_crash=
    attributes on a CodeBlock, shared by canvas_filter,
    code_include_filter, and include_deps_filter -- all three need the
    same parsing and the same derived .out/.stout/.crash path shape.

    crash= and compile-fail= are deliberately separate: crash= means
    "this program is expected to crash at runtime, build its .crash
    artifact rather than treating a non-zero exit as a build failure";
    compile-fail= means "this Java source is expected to fail
    compilation, capture the compiler diagnostic instead of treating it
    as a runtime crash." hide_crash= controls only whether code_filter
    renders that traceback; it does nothing without crash= or
    compile-fail= being set."""
    include: Optional[str]
    output: bool
    stout: bool
    crash: bool
    compile_fail: bool
    hide_crash: bool
    chunk: Optional[str] = None
    plot: Optional[int] = None

    @classmethod
    def from_element(cls, elem):
        return cls(
            include=elem.attributes.get("include"),
            output=bool(elem.attributes.get("output")),
            stout=bool(elem.attributes.get("stout")),
            crash=bool(elem.attributes.get("crash")),
            compile_fail=bool(
                elem.attributes.get("compile-fail")
                or elem.attributes.get("compile_fail")
            ),
            hide_crash=bool(elem.attributes.get("hide_crash")),
            chunk=elem.attributes.get("chunk"),
            plot=cls._parse_plot(elem.attributes.get("plot")),
        )

    @staticmethod
    def _parse_plot(raw):
        """plot=true means figure 1 of the chunk; plot=2 means figure
        2 -- a chunk producing a different count than asked for is a
        build error, not something discoverable without running R."""
        if not raw or raw.lower() == "false":
            return None
        if raw.lower() == "true":
            return 1
        return int(raw)

    @property
    def stem(self):
        return os.path.splitext(self.include)[0]

    @property
    def chunk_stem(self):
        """The stem a chunk-aware artifact is named from --
        <stem>_<chunk> when chunk= is set, today's whole-file <stem>
        when it isn't, so existing Python pages see no behaviour
        change."""
        if self.chunk:
            return self.stem + "_" + self.chunk
        return self.stem

    @property
    def output_path(self):
        return self.chunk_stem + ".out"

    @property
    def stout_path(self):
        return self.chunk_stem + ".stout"

    @property
    def crash_path(self):
        return self.chunk_stem + ".crash"

    @property
    def compile_fail_path(self):
        return self.crash_path

    @property
    def plot_path(self):
        """<stem>_<chunk>-<n>.png -- only meaningful when plot= is set."""
        return self.chunk_stem + "-" + str(self.plot) + ".png"

    def referenced_paths(self):
        """Every file this directive touches."""
        paths = [self.include] if self.include else []
        if self.output:
            paths.append(self.output_path)
        if self.stout:
            paths.append(self.stout_path)
        if self.crash or self.compile_fail:
            paths.append(self.crash_path)
        if self.plot:
            paths.append(self.plot_path)
        return paths
