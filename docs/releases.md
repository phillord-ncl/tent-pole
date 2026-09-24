# Releases

## 0.6.0

- Added `tent-pole build`, a [doit](https://pydoit.org/)-based
  replacement for the old make-based rules: builds a plain directory
  of markdown pages with no configuration at all, recurses into child
  module directories on its own, and a course needing extra rules adds
  a `dodo.py` doing `from tent_pole.doit_rules import *` to extend it.
  A bare source-file stem resolves to its build target automatically
  (`tent-pole build hello` for `hello.md`). See
  [docs/new-project.md](new-project.md).
- Added `tent-pole build clean [-a]`, recursing into child module
  directories the same way `build` itself does.
- Added `tent-pole build reorder`, the same as `module reorder` but
  reachable as part of a build.
- Added `tent-pole help [command]`, the same idea as `git help`.
- `tent-pole init`/`import` no longer scaffold a `Makefile` -- `build`
  needs no local build file at all for the common case.
- Fixed: `page push` now records its own local push-tracking state as
  part of the same push, instead of leaving it to a separate `dump`
  step -- a failure between the two used to leave a successful push
  permanently unrecorded, so every retry re-tripped the drift guard
  against tent-pole's own prior push.
- Fixed: `page push` recreates a page that's been deleted independently
  of tent-pole instead of crashing with "no page found".

## 0.5.0

- Added `tent-pole import <course> [directory]` -- pulls an existing
  Canvas course down to a local tent-pole project: pages to
  best-effort markdown (including reconstructing `{include=...}`
  directives against the real downloaded source, not a frozen copy of
  the rendered output), their images/files, and module structure,
  scaffolded like `tent-pole init`. Strictly read-only against Canvas.
  Quizzes and other non-page module items are reported as not
  imported, never silently dropped. See `docs/import-a-course.md`.
- Fixed: a plain (no-language) code block's content wasn't
  HTML-escaped before being spliced into `<pre><code>`, so tag-shaped
  text (a Python traceback's `<module>`, for instance) silently
  vanished when Canvas's sanitizer stripped it as markup.
- Fixed: `file push` now passes `on_duplicate="overwrite"` -- Canvas's
  own upload API defaults to renaming instead, so re-pushing an
  already-uploaded file silently created a duplicate instead of
  replacing it.
- Fixed: `.tpp`/`.tpf`/`.tpm`/`.tpq`/`.out`/`.stout`/`.crash`/
  `.test_out` are now `.PRECIOUS`, alongside the existing `.html` --
  GNU Make was silently deleting them as build intermediates after a
  successful `make`, disabling `push`'s drift checks and, for files,
  risking an unconditional re-upload on the next build.

## 0.4.0

- Removed `--tent-pole-dev` from `tent-pole init` -- `pipx install
  --editable` covers the same need without any wrapper-script
  machinery. See `docs/migration.md` for repos that adopted the old
  flag's generated `dev-scripts/`.
- Switched the build backend to `poetry-core`, needed for `pipx
  install --editable` to work at all (the old `poetry.masonry.api`
  backend doesn't implement PEP 660).
- Fixed: dpath's `MERGE_REPLACE` flag was removed in dpath 2.1,
  breaking config loading on a fresh install; now uses
  `dpath.MergeType.REPLACE`, and the loose `dpath` constraint that let
  this happen is tightened to `^2.1.0`.

## 0.3.0

- Author Canvas quizzes from a `.quiz.md` markdown dialect --
  `tent-pole quiz push`, plus a `%.tpq`/`%.quiz.full.html` Make
  pattern. See `docs/quiz-markdown.md`. Multiple-choice/multiple-
  answers/essay questions, question groups (including an empty one),
  and code blocks (`include=`/`output=`/`stout=`/`crash=`, plus a new
  `hide_crash=`) are supported; matching/numerical/fill-in-multiple-
  blanks/question banks aren't yet.
- A `[module] items` entry can reference a quiz by its `.quiz.md`
  filename, the same way a page item already does, instead of a raw
  Canvas id.
- A markdown link to a `.quiz.md` file resolves to the quiz's real
  Canvas url, once pushed.
- Fixed: "Take from:" read "Taken from:" in code-block attribution
  links.
- Fixed: an answer's markup (e.g. inline code) rendered as literal
  HTML tags instead of formatted text -- Canvas needs a separate
  `answer_html` field alongside `answer_text`, not just the latter.

## 0.2.0

- Shared Makefile includes (`tent_pole/make-rules/`, `tent_pole/bin/`),
  located via a new `tent-pole pkg-dir` command.
- `file dump --wait`.
- Non-destructive `module reorder` and a new `module dump`.
- `include-deps-filter`, auto-generating Make dependencies from a
  page's `include=`/image/link usage.
- `config api-url`.
- `page push`/`dump`/`update`/`verify` and `module reorder` resolve a
  page by its actual url rather than assuming it matches the page's
  name -- a page whose title has ever collided with a deleted page's
  (Canvas reserves that slug permanently) no longer crashes the build.
- Internal page-to-page markdown links resolve to the linked page's
  real url too, once known, instead of silently breaking after the
  same kind of url drift.
- The python output-capture rules (`%.out`/`%.crash`/`%.stout`/
  `%.test_out`) now run from the script's own directory, not whichever
  directory happened to invoke the rule.
- Quiet, Automake-style `make` output by default -- a short status
  line per recipe instead of the full command; `make V=1` for full
  command visibility.
- `module reorder`'s per-item message now describes adding a module
  item rather than misleadingly saying it's creating the page itself.

## 0.1.0

Initial release.
