import panflute as pf

from tent_pole import code_include_filter


def test_no_include_leaves_block_unchanged():
    elem = pf.CodeBlock("plain text", classes=["python"])
    assert code_include_filter.code_filter(elem, doc=None) is None


def test_non_codeblock_elements_ignored():
    para = pf.Para(pf.Str("hello"))
    assert code_include_filter.code_filter(para, doc=None) is None


def test_include_substitutes_file_content_into_codeblock(tmp_path):
    source = tmp_path / "snippet.py"
    source.write_text("print('hi')")

    elem = pf.CodeBlock("", classes=["python"], attributes={"include": str(source)})
    result = code_include_filter.code_filter(elem, doc=None)

    assert len(result) == 1
    block = result[0]
    ## Stays a CodeBlock -- pandoc's own writer does the highlighting,
    ## unlike canvas-filter which pre-renders to a RawBlock.
    assert isinstance(block, pf.CodeBlock)
    assert block.text == "print('hi')"
    assert block.classes == ["python"]


def test_output_attribute_appends_captured_output(tmp_path):
    source = tmp_path / "demo.py"
    source.write_text("print('hi')")
    (tmp_path / "demo.out").write_text("hi\n")

    elem = pf.CodeBlock(
        "", classes=["python"],
        attributes={"include": str(source), "output": "true"},
    )
    result = code_include_filter.code_filter(elem, doc=None)

    assert len(result) == 3
    assert isinstance(result[1], pf.Para)
    assert result[1].content[0].text == "Outputs:"
    assert isinstance(result[2], pf.CodeBlock)
    assert result[2].text == "hi\n"


def test_stout_attribute_appends_captured_repl_transcript(tmp_path):
    source = tmp_path / "demo.py"
    source.write_text("x = 1")
    (tmp_path / "demo.stout").write_text(">>> x = 1\n")

    elem = pf.CodeBlock(
        "", classes=["python"],
        attributes={"include": str(source), "stout": "true"},
    )
    result = code_include_filter.code_filter(elem, doc=None)

    assert len(result) == 3
    assert result[1].content[0].text == "Prints:"
    assert result[2].text == ">>> x = 1\n"


def test_crash_attribute_appends_captured_traceback(tmp_path):
    source = tmp_path / "demo.py"
    source.write_text("1/0")
    (tmp_path / "demo.crash").write_text("ZeroDivisionError\n")

    elem = pf.CodeBlock(
        "", classes=["python"],
        attributes={"include": str(source), "crash": "true"},
    )
    result = code_include_filter.code_filter(elem, doc=None)

    assert len(result) == 3
    assert result[1].content[0].text == "Crashes:"
    assert result[2].text == "ZeroDivisionError\n"


def test_hide_crash_suppresses_traceback_but_keeps_crash_declared(tmp_path):
    """crash= and hide_crash= are separate: crash= alone still means
    "this program is expected to crash" (a real "will this code
    crash?" quiz question needs that, or the build fails), but
    rendering the traceback right there would answer the question for
    free -- hide_crash= suppresses only the rendering."""
    source = tmp_path / "demo.py"
    source.write_text("1/0")
    (tmp_path / "demo.crash").write_text("ZeroDivisionError\n")

    elem = pf.CodeBlock(
        "", classes=["python"],
        attributes={"include": str(source), "crash": "true", "hide_crash": "true"},
    )
    result = code_include_filter.code_filter(elem, doc=None)

    assert len(result) == 1
    assert "Crashes:" not in [getattr(b, "text", None) for b in result]


def test_no_language_class_include_still_substitutes(tmp_path):
    source = tmp_path / "output.txt"
    source.write_text("some captured text")

    elem = pf.CodeBlock("", classes=[], attributes={"include": str(source)})
    result = code_include_filter.code_filter(elem, doc=None)

    assert len(result) == 1
    assert result[0].text == "some captured text"
