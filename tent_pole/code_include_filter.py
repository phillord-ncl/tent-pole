from panflute import *

from .code_include_attrs import CodeIncludeAttrs
from .spin_chunks import split_chunks


def code_filter(elem, doc):
    """Replaces {include=path} code blocks with the named file's
    content. Same include=/output=/stout=/crash=/chunk=/plot= syntax
    as canvas-filter's own code_filter, but with no Canvas API
    dependency."""
    if type(elem) != CodeBlock:
        return None

    attrs = CodeIncludeAttrs.from_element(elem)
    if not attrs.include:
        return None

    with open(attrs.include) as fh:
        content = fh.read()

    ## chunk= only changes what's shown here -- it never changes what
    ## actually executed to produce output_path/stout_path/crash_path/
    ## plot_path, which already ran the chunk's full dependency chain.
    elem.text = split_chunks(content)[attrs.chunk] if attrs.chunk else content

    blocks = [elem]

    if attrs.output:
        with open(attrs.output_path) as fh:
            blocks.append(Para(Str("Outputs:")))
            blocks.append(CodeBlock(fh.read()))

    if attrs.stout:
        with open(attrs.stout_path) as fh:
            blocks.append(Para(Str("Prints:")))
            blocks.append(CodeBlock(fh.read()))

    if attrs.crash and not attrs.hide_crash:
        with open(attrs.crash_path) as fh:
            blocks.append(Para(Str("Crashes:")))
            blocks.append(CodeBlock(fh.read()))

    if attrs.plot:
        blocks.append(Para(Str("Plot:")))
        blocks.append(Para(Image(Str(attrs.plot_path), url=attrs.plot_path)))

    return blocks


def main(doc=None):
    return run_filter(code_filter, doc=doc)


if __name__ == '__main__':
    main()
