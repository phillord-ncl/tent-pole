# Import an existing course

If a course already has content on Canvas -- hand-authored, or from
before tent-pole existed -- `tent-pole import` brings it under
tent-pole's management, without retyping anything.

This is a **lossy, best-effort** reverse-engineering, not an exact
copy: reconstructed markdown needs a read-through and a tidy-up
afterwards, and some content types can't be reconstructed at all (see
"What isn't imported" below). It's strictly read-only against
Canvas -- nothing is pushed back until you run `make pages` yourself.

## 1. Import

You should ensure your API key is [configured](configure.md) first.

```
tent-pole import <course> [directory]
```

`<course>` accepts a numeric id, a course code, or a name -- same
resolution as `-c`/`--course` elsewhere. `directory` defaults to a
slugified version of the course's name if omitted. The target
directory must not already exist with content in it.

This scaffolds a project exactly like [`tent-pole
init`](new-project.md) would, except populated from the live course:

- Each page, reverse-engineered from its Canvas HTML to markdown on a
  best-effort basis, and the images/files it embeds, downloaded
  alongside it.
- Module structure, reconstructed as a `tent-pole.toml` per module
  subdirectory -- see [organise a module](organise-a-module.md) for
  what that file means.
- A page belonging to no module is written at the project root
  instead of in a module subdirectory.
- `git init`, unless `--no-git`.

## 2. Read through and tidy up

Nothing is verified byte-for-byte -- open the generated markdown and
check it reads sensibly before trusting it. A couple of things worth
knowing about up front:

- Syntax-highlighted code blocks come back as plain code blocks: the
  highlighting itself isn't markdown-representable, and there's no way
  to recover whether a block was originally written with
  `{include=...}` (see [include code](include-code.md)) -- the
  directive is gone, only its rendered output survives.
- A link to another page being imported in the same run is rewritten
  to a bare `[text](page-slug)` link, matching how tent-pole expects
  page links to be written. A link to anything outside the import (a
  page in another course, an external site) is left exactly as Canvas
  had it.

## 3. Build and push

Once you're happy with the markdown, treat it like any other tent-pole
project:

```
make pages
make reorder
```

The first `make pages` after an import is a genuine first push --
`import` doesn't pre-record any "this is already up to date" state,
even though the content originally came from Canvas.

## What isn't imported

Printed as a one-line notice per item, never silently dropped:

- **Quizzes.** There's no reverse path from a live quiz back to
  `.quiz.md` -- reconstructing one would mean fully re-deriving its
  question/answer structure from the Canvas API, which `import`
  doesn't attempt. The quiz stays on Canvas as it is; only the notice
  that it was skipped shows up locally.
- Assignments, discussions, external tools/URLs, and sub-headers as
  module items -- none of these have a markdown-authored forward path
  in tent-pole either, so there's nothing to reconstruct them into.

## `import` options

- `--no-git` -- don't run `git init`.
