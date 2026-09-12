from panflute import *

from .code_include_attrs import CodeIncludeAttrs


def code_filter(elem, doc):
    """Replaces {include=path} code blocks with the named file's
    content. Same include=/output=/stout=/crash= syntax as
    canvas-filter's own code_filter, but with no Canvas API dependency."""
    if type(elem) != CodeBlock:
        return None

    attrs = CodeIncludeAttrs.from_element(elem)
    if not attrs.include:
        return None

    with open(attrs.include) as fh:
        elem.text = fh.read()

    blocks = [elem]

    if attrs.output:
        with open(attrs.output_path) as fh:
            blocks.append(Para(Str("Outputs:")))
            blocks.append(CodeBlock(fh.read()))

    if attrs.stout:
        with open(attrs.stout_path) as fh:
            blocks.append(Para(Str("Prints:")))
            blocks.append(CodeBlock(fh.read()))

    if attrs.crash:
        with open(attrs.crash_path) as fh:
            blocks.append(Para(Str("Crashes:")))
            blocks.append(CodeBlock(fh.read()))

    return blocks


def main(doc=None):
    return run_filter(code_filter, doc=doc)


if __name__ == '__main__':
    main()
