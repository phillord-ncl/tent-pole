# Markdown Features: tent-pole Beta Test

This is a single-page tent-pole beta test, covering every markdown feature
used in the real coursework. It exists purely to check that pandoc +
canvas-filter + tent-pole render each one correctly when pushed to Canvas.
Each section below says what you should see on the published Canvas page —
check each one off as you review. A second, near-empty page exists
alongside this one purely to confirm tent-pole can place multiple pages
into a Canvas module/section.

## Text formatting

This paragraph has **bold text**, *italic text*, and `inline code`.
**Check:** bold is bold, italic is slanted, and the code snippet is in a
monospace font with a light background.

## Lists

Unordered, with a nested item:

* First item
* Second item
    * Nested item under second
* Third item

Ordered:

1. Step one
2. Step two
3. Step three

**Check:** bullets and numbers render correctly, and the nested item is
visibly indented under "Second item".

## Blockquote

> This paragraph should appear as an indented, visually distinct quote
> block, not as plain body text.

**Check:** the paragraph above is styled as a blockquote.

## Table

| Feature   | Expected result       |
|-----------|------------------------|
| Headers   | Bold header row        |
| Alignment | Columns line up        |

**Check:** a two-column table with a bold header row.

## Code block (inline, no include)

```python
def greet(name):
    return f"Hello, {name}!"
```

**Check:** this renders as syntax-highlighted Python (keywords, strings,
etc. in different colours), not plain unstyled text.

## Links

An external link: [Python docs](https://docs.python.org/3/).

An internal link to [page 2 of this test](markdown-features-2), written as
a bare page slug exactly the way the real coursework links between pages.

**Check:** the external link opens the Python docs in a new context as
normal; the internal link takes you to "Markdown Features 2" *within this
Canvas course* (this is relative-URL resolution in the browser, not
anything canvas-filter rewrites -- confirms that pattern still works).

## Included source and its captured output

```{.python include=demo.py output=true}
```

**Check:** you should see four things, in order -- the syntax-highlighted
contents of `demo.py`; a "Taken from: demo.py" link that downloads the
original source file; an "Outputs:" label; and a code block showing
`1 4 9 16 25` each on its own line (the captured stdout from actually
running `demo.py`).

## Interactive shell transcript (stout)

```{.python include=repl_demo.py stout=true}
```

**Check:** below the "Taken from: repl_demo.py" link, a "Prints:" label and
a code block showing an interactive-shell transcript -- `>>> x = 3`,
`>>> y = 4`, `>>> x + y` followed by `7`, with the prompts included (this
is different from "output" above: it's captured as if typed at a Python
REPL, not just the script's own stdout).

## Crash and traceback (crash)

```{.python include=crash_demo.py crash=true}
```

**Check:** below the "Taken from: crash_demo.py" link, a "Crashes:" label
and a code block showing a `ZeroDivisionError` traceback (the script
deliberately divides by zero) -- confirms tent-pole/canvas-filter can
display a script's failure, not just its successful output.

## Image

![A small orange/blue test checkerboard](test-image.png "Test image")

**Check:** a small (64x64) orange-and-blue checkerboard image appears
inline, served from this course's Canvas files.

## Media (video)

[test-video.mp4](test-video.mp4)

**Check:** an inline video player (not a download link) appears, roughly
400x225px. It should actually play: a few seconds of a moving colour-bar
test pattern with a 440Hz tone.

---

If everything above checked out, tent-pole's markdown pipeline is working
correctly against beta.
