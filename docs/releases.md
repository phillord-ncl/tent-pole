# Releases

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
