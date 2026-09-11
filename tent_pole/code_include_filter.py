import os

from panflute import *


def code_filter(elem, doc):
    """Replaces {include=path} code blocks with the named file's
    content. Same include=/output=/stout=/crash= syntax as
    canvas-filter's own code_filter, but with no Canvas API dependency."""
    if type(elem) != CodeBlock:
        return None

    include = elem.attributes.get("include")
    if not include:
        return None

    with open(include) as fh:
        elem.text = fh.read()

    blocks = [elem]
    name = os.path.splitext(include)[0]

    if elem.attributes.get("output"):
        with open(name + ".out") as fh:
            blocks.append(Para(Str("Outputs:")))
            blocks.append(CodeBlock(fh.read()))

    if elem.attributes.get("stout"):
        with open(name + ".stout") as fh:
            blocks.append(Para(Str("Prints:")))
            blocks.append(CodeBlock(fh.read()))

    if elem.attributes.get("crash"):
        with open(name + ".crash") as fh:
            blocks.append(Para(Str("Crashes:")))
            blocks.append(CodeBlock(fh.read()))

    return blocks


def main(doc=None):
    return run_filter(code_filter, doc=doc)


if __name__ == '__main__':
    main()
