Tent-Pole: Command Line Tools for Canvas
=========================================

Tent-pole is a command-line client for [Canvas
LMS](https://www.instructure.com/canvas), built around managing course
content as local markdown files under version control rather than
editing it through the Canvas web UI. It manages both the
transformation between markdown and HTML suitable for canvas, and
syncing files between the local machine and canvas.

Tent-pole works in concert with an existing command line environment,
meaning that it can be adapted to generate canvas pages from any kind
of source, including live code that can be run to generate output
through the use of GNU Make. HTML generation is done by pandoc, with
tent-pole supplied filters to support code inclusion. The organisation
of pages into canvas modules uses TOML configuration.

Requirements: Python >= 3.14.
Optional: Pandoc, if using the filters.
Optional: GNU Make for building complete courses.


Installation
------------

With [Poetry](https://python-poetry.org/):

```
poetry install
poetry run tent-pole --help
```

See [docs/install.md](docs/install.md) for a `PATH`-installed binary,
pipx, and no-install options.


Configuration
--------------

Tent-pole reads settings from `tent-pole.toml`, cascaded from your
user config directory and every `tent-pole.toml` between the current
directory and the nearest enclosing `.git` root. A minimal user
config:

```toml
[general]
api_key = "put-your-api-key-in-here"

[course]
id = "23212"
```

See [docs/configure.md](docs/configure.md) for the merge order, `-c`/
`--course`, and pointing at a beta/sandbox instance instead of the
real course.


Documentation
--------------

Task-oriented howtos, in `docs/`:

- [Install tent-pole](docs/install.md)
- [Start a new project](docs/new-project.md)
- [Import an existing course](docs/import-a-course.md)
- [Configure](docs/configure.md)
- [Write a page](docs/write-a-page.md)
- [Write a quiz](docs/write-a-quiz.md)
- [Organise a module](docs/organise-a-module.md)
- [Include code output in a page or quiz](docs/include-code.md)

Reference material:

- [docs/quiz-markdown.md](docs/quiz-markdown.md) -- the `.quiz.md`
  dialect, field by field.
- [docs/migration.md](docs/migration.md) -- bringing an existing
  course repo's Makefile up to date with the current shared rules.
- [docs/releases.md](docs/releases.md) -- changelog.


Command Reference
------------------

Tent-pole uses a subcommand structure: `tent-pole <group> <command>
[args]`.

### config

- `api-key` -- print the configured API key
- `course` -- print the configured course identifier
- `dump` -- print the fully merged configuration

### course

- `data <course>` -- print information about a course
- `modules <course>` / `pages <course>` / `files <course>` /
  `assignments <course>` / `quizzes <course>` / `discussions <course>`
  -- list that kind of content in a course

`<course>` accepts a numeric id, a course code (exact match), or a
name (substring match).

### module

- `data <module>` -- print information about a module
- `list <module>` -- list items in a module
- `create [name]` -- create a module, unless one with that exact name
  already exists (falls back to the configured module if `name` is
  omitted)
- `delete <module>` -- delete a module, with a y/n confirmation prompt
- `addpage <module> <page-url> [indent]` -- add a page to a module
- `addhead <module> <title> [indent]` -- add a sub-header to a module
- `addfile <module> <file-id> [indent]` -- add a file to a module
- `reorder` -- bring the configured module's item list in line with
  `[module] items` in `tent-pole.toml`

`<module>` accepts a numeric id or a name (substring match). See
[docs/organise-a-module.md](docs/organise-a-module.md).

### page

- `data <page-url>` -- print information about a page
- `create <file>` -- create a page from a local file, erroring if a
  page of that name already exists
- `update <file>` -- push a local file's contents to an *existing*
  page
- `push <file>` -- create-or-update: the common case
- `dump <file>` -- record the page's current remote state next to the
  local file, as `<file minus extension>.tpp`
- `check <file>` -- local-only: has `<file>` changed since it was
  last pushed? (compares against the recorded `.tpp`)
- `verify <file>` -- `check`, plus: was the page edited on Canvas by
  someone else since the last push, or (for pages built with
  `canvas-filter`) does its live compile-timestamp marker no longer
  match what was recorded?

See [docs/write-a-page.md](docs/write-a-page.md).

### file

- `data <file>` -- print information about an uploaded file
- `push <file>` -- upload/replace a file, into a fixed `tent-pole`
  folder on Canvas (so "did tent-pole manage this" is a cheap check)
- `dump <file>` -- record the file's current remote state as
  `<file>.tpf`
- `check <file>` -- local-only: has `<file>` changed since it was
  last pushed?
- `verify [--deep] <file>` -- `check`, plus: has the remote file's
  size changed? `--deep` downloads and hashes the remote file instead,
  for a byte-exact comparison.

`file push`/`dump` and `page push`/`dump` are meant to be run as a
pair -- see [docs/write-a-page.md](docs/write-a-page.md), which covers
embedding a pushed file/image/video into a page.

### quiz

- `push <file>` -- create-or-update a Canvas quiz from a `.quiz.md`
  file
- `push --dry-run <file>` -- parse and print the structure, no network
  access

See [docs/write-a-quiz.md](docs/write-a-quiz.md) and
[docs/quiz-markdown.md](docs/quiz-markdown.md).


Pandoc Filters
---------------

Course content is normally written as Markdown and compiled through
Pandoc. Tent-pole ships two filters, both understanding the same
`{include=... output=... stout=... crash=...}` code-block attributes:

- `canvas-filter` resolves a Markdown document into self-contained
  HTML meant for `tent-pole page push`: local images and links become
  Canvas API URLs, `.mp4` links become an embedded media player, and
  the result carries a hidden compile-timestamp marker that `page
  verify` checks against later.
- `code-include-filter` resolves the same syntax with no Canvas API
  access at all -- for building static output (slides, PDF, a
  standalone HTML file to open in a browser) where Pandoc itself
  should syntax-highlight per output format instead.

See [docs/include-code.md](docs/include-code.md) for the
`include=`/`output=`/`stout=`/`crash=` attributes themselves, and
[docs/write-a-page.md](docs/write-a-page.md) for a typical push
pipeline.


Development
------------

`dev/sample-course/` is a standalone fixture exercising every
Markdown/`canvas-filter` feature, plus `.quiz.md` -> Canvas quiz, for
reviewing a push against a test Canvas instance by eye -- see its own
`README.md`.

```
poetry install --with dev
poetry run pytest              # unit tests; skips anything marked `canvas`
poetry run pytest -m canvas    # also exercise a real Canvas sandbox course
poetry run pre-commit run --all-files
```


License
--------

GNU Lesser General Public License v3 -- see `COPYING.lesser`.
