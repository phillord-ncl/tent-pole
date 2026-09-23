# Quiz markdown

`.quiz.md` files author Canvas quizzes the same way `.md` files author
pages -- reusing pandoc's own constructs (front matter, header
attributes, task-list checkboxes, code-block attributes) rather than a
separate quiz-specific syntax. See `dev/sample-course/
question-types-quiz.quiz.md` and `question-groups-quiz.quiz.md` for
real, working examples of everything below.

Reference material, not a tutorial -- see [write a quiz](write-a-quiz.md)
for a walkthrough. Preliminary: real per-question/group identity,
drift detection, and a `tent-pole.toml`-driven `[quizzes]` config
section (replacing the `.quiz.md` extension-sniffing convention below)
are all still open -- see `next_steps.md`.

## File recognition

The `.quiz.md` extension. `tent-pole build` tells a quiz apart from an
ordinary page by it automatically -- a directory can freely mix `.md`
and `.quiz.md` files, nothing to configure either way.

## Front matter

YAML front matter maps near-verbatim to quiz-level kwargs (`title`,
`quiz_type`, `allowed_attempts`, `scoring_policy`, etc). `points_
possible` is dropped if present, with a warning -- Canvas computes it
from questions/groups, it can't be set directly.

## Preamble

Body content between the front matter and the first header becomes
the quiz's `description` -- the text shown above the first question.

## Questions

A header carrying `.question`, plus pandoc header attributes:

- `points="N"` -> `points_possible`
- `type="..."` -> `question_type`, via a short alias (`essay` ->
  `essay_question`, and so on) -- required whenever it isn't
  unambiguous from checkboxes (see Answers below), never inferred for
  an essay/text-only question.

The header's own text becomes `question_name`; everything until the
next header becomes `question_text` (rendered to HTML, code blocks
highlighted the same way a page's are).

## Answers

A checkbox list (`- [x]`/`- [ ]`) immediately under a question becomes
its answers. `[x]` -> weight 100, `[ ]` -> weight 0. Type inference:
exactly one `[x]` -> `multiple_choice_question`; more than one ->
`multiple_answers_question`. No checkbox list at all -> essay/
text-only, and `type=` must then be written explicitly.

## Groups

A header one level shallower than its questions, carrying `.group`
plus:

- `pick="N"` -> `pick_count`
- `points="N"` -> `question_points`

A group with zero questions under it is valid -- Canvas still counts
its `pick_count`/`question_points` toward the quiz's own total, even
though there's nothing to actually pick.

## Code blocks

The same `include=`/`output=`/`stout=`/`crash=` attributes a page uses
(see [include-code.md](include-code.md)), plus one quiz-specific
addition:

- `hide_crash=` suppresses the rendered "Crashes:" section that
  `crash=` would otherwise always show. `crash=` alone still means
  "this program is expected to crash, build its `.crash` artifact
  rather than failing the build" -- `hide_crash=` is what actually
  lets a real "will this code crash?" question exist without
  answering itself.

## Publishing

```
tent-pole quiz push <file>.quiz.md          # create or update
tent-pole quiz push --dry-run <file>.quiz.md  # parse only, no network
```

Every push deletes and recreates every question and group on the quiz
-- nothing in the markdown gives a question or group a stable identity
across edits the way a page's url does, so this is a full replace, not
a diff. Refuses to push over a published quiz, or one with any
submissions, without `--force` (that would destroy submission-linked
data).

`tent-pole build` provides both `<name>.tpq` (push, via
`tent-pole build <name>`) and `tent-pole build quiz_full` (a local,
no-Canvas-access preview, the same idea as a page's `full`).

## Linking

- A `[module] items` entry can reference a quiz by its `.quiz.md`
  filename (`{type="Quiz", id="some-quiz.quiz.md"}`), the same way a
  page item is referenced by filename -- resolved via the quiz's own
  `.tpq`.
- A markdown link to a `.quiz.md` file, from a page or another quiz,
  resolves to the quiz's real Canvas url once it's been pushed.

## Not supported yet

Matching, numerical, fill-in-multiple-blanks, and question-bank
question types -- each needs the same hand-built-and-inspected
validation the supported types already got before its markdown shape
can be trusted.
