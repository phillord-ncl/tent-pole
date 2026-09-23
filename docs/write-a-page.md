# Write a page

A Canvas page is written as an ordinary Markdown file and pushed
through Pandoc. Assumes a project already set up as in
[start a new project](new-project.md).

## The basics

```
echo '# Hello, world' > hello.md
tent-pole build hello
```

`tent-pole build hello` resolves the bare stem to `hello.tpp` and runs
pandoc through `canvas-filter`, `page push`, and `page dump` for you --
much simpler than typing out that sequence by hand. `tent-pole build`
with no argument does the same for every page in the directory.

Under the hood, that one command is exactly this:

```
pandoc --filter=canvas-filter hello.md > hello.html
tent-pole page push hello.html
tent-pole page dump hello.html
```

The Canvas page name comes from the file name: `page-1.md` ->
`page-1` (underscores become hyphens). `page dump` records the page's
current remote state next to the file, as `hello.tpp` -- do this after
every push, since later commands (`check`, `verify`, links between
pages) read it back. `tent-pole build` always does this for you; only
reach for the pieces individually when you need finer control than a
single build step gives you.

## Everyday commands

- `tent-pole page push <file>` -- create-or-update; the one you'll use
  almost always.
- `tent-pole page check <file>` -- has the local file changed since
  last pushed? Local-only, no network.
- `tent-pole page verify <file>` -- `check`, plus: was the page edited
  on Canvas by someone else since the last push?
- `tent-pole page create <file>` / `update <file>` -- the two halves
  of `push`, for when create-vs-update needs to be explicit (`create`
  errors if the page already exists; `update` errors if it doesn't).

## Linking to another page

Write a bare internal link using the *source* file's slug, the same
way the real page will resolve it once both are pushed:

```markdown
See [page 2](markdown-features-2) for more.
```

`canvas-filter` resolves this to the linked page's real Canvas url at
build time -- it survives even if that page's url has drifted from its
filename (Canvas permanently reserves a deleted page's old slug, so a
recreated page can end up at a different url than you'd expect).

## Embedding an image, file, or video

Push the file first, so `canvas-filter` has somewhere to point the
link/embed:

```
tent-pole file push test-image.png
tent-pole file dump test-image.png
pandoc --filter=canvas-filter page.md > page.html
```

```markdown
![Alt text](test-image.png "Title")

[a-video.mp4](a-video.mp4)
```

An image becomes an inline `<img>`; a `.mp4` link becomes an embedded
media player instead of a download link. Video uploads need
`tent-pole file dump --wait` instead of a plain `dump` -- Canvas
returns a placeholder id until transcoding finishes, and the embed
needs the real one. With `tent-pole build` from
[start a new project](new-project.md), this all happens automatically:
every image/file/link a page actually references is discovered
straight from its markdown and pushed as its own build step ahead of
the page itself -- no separate `file push` step to remember.

## Including a script's source and output

A code block can also pull in a script's own source and what it
produces when run, instead of you pasting either in by hand -- see
[include code output in a page or quiz](include-code.md) for the
attributes and what they render.

## Standalone preview, no Canvas access

```
tent-pole build full
```

builds `<file>.full.html` via `code-include-filter` instead of
`canvas-filter` -- a self-contained file to open directly in a
browser, useful while iterating before anything touches Canvas.

## More markdown features

`dev/sample-course/markdown-features-1.md` in the tent-pole checkout
is a working, annotated example exercising every feature above plus
tables, blockquotes, and nested lists -- copy from there if in doubt
about what pandoc/canvas-filter support.
