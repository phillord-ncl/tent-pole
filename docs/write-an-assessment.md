# Write an assessment

A `.rubric.toml` file authors a Canvas assignment and the rubric used
to mark it, together, from one source file. This walks through
building one up from nothing; see "Field reference" below for the
exact names once the shape is familiar.

## 1. The assignment

```toml
[assignment]
title = "Exercise 2: Loops and Lists"
description = "assignment-description.md"
points_possible = 20
submission_types = ["online_upload"]
published = false
```

`description` is a path to an ordinary page -- the same `.md` file a
`tent-pole page push` would take, built to `.html` first and read from
there (so write it, and preview it, exactly like any other page; see
[write a page](write-a-page.md)). `points_possible` should equal the
sum of every criterion's own `points` below -- that's the total a
student sees.

## 2. The rubric's criteria

```toml
[[criteria]]
id = "correctness"
description = "Correctness"
long_description = """
Code produces the correct output for every example in the brief,
including the edge cases listed under 'Things to check'.
"""
points = 10

[[criteria.ratings]]
id = "full"
description = "Fully correct"
points = 10

[[criteria.ratings]]
id = "partial"
description = "Mostly correct, minor edge-case failures"
points = 6

[[criteria.ratings]]
id = "none"
description = "Does not run, or wrong output throughout"
points = 0
```

Each `[[criteria]]` block is one row of the rubric; each
`[[criteria.ratings]]` block under it is one performance level a
marker can pick. `id` on either is tent-pole's own bookkeeping --
Canvas assigns its own internal ids on push, and (confirmed live)
doesn't keep them stable across an edit, so tent-pole's `id` exists
purely so a human can keep track of "this is the same row" while
editing the TOML, not to control Canvas's own id.

An optional `[rubric]` table controls the rubric itself, separately
from the assignment it grades:

```toml
[rubric]
free_form_criterion_comments = true
```

`free_form_criterion_comments` lets a marker type free text against a
criterion instead of only picking a predefined rating. Everything in
`[rubric]` has a sensible default if left out -- the rubric's own
title defaults to `"<assignment title> Rubric"`.

## 3. Push it

```
tent-pole rubric push example.rubric.toml
```

or `tent-pole build example` once it's built at least once (resolves
the bare stem to `example.tpa`). Creates the assignment and rubric
together on first push; a later push updates both *in place* -- same
assignment id, same rubric id, not a delete-and-recreate.

Tent-pole refuses to push over an assignment that's published, that
has a real student submission, or whose rubric already has a recorded
mark against it, unless you pass `--force`. Forcing anyway replaces
the rubric's whole criteria set in one go (not a per-criterion diff),
which can orphan any marking already recorded against the old
criteria/ratings -- their Canvas-side ids change on every update, so
there is no way to preserve a link from an old mark to the row it was
against.

## 4. Link to it from a page

```markdown
Complete [Exercise 2](example.rubric.toml) before the next lecture.
```

A markdown link to a `.rubric.toml` file resolves to the assignment's
real Canvas url once it has been pushed -- same idea as a link to a
`.quiz.md` file (see [write a quiz](write-a-quiz.md)).

## 5. Put it in a module

Once pushed at least once, reference it from `tent-pole.toml` the same
way a page or quiz is referenced -- see
[organise a module](organise-a-module.md#item-types). This matters
more than it does for a page or quiz on a course where the Assignments
tab itself is hidden from students: with nothing else linking to it, a
published-but-unlisted assignment may not be reachable by students at
all.

## Field reference

- `[assignment]`: `title`, `description` (a `.md` page path),
  `points_possible`, `submission_types` (a list, e.g.
  `["online_upload"]`), `published`.
- `[rubric]` (optional): `title` (default `"<assignment title> Rubric"`),
  `free_form_criterion_comments`, `hide_score_total`.
- `[[criteria]]`: `id` (tent-pole's own, not Canvas's), `description`,
  `long_description` (a TOML multi-line `"""..."""` string reads well
  for anything more than a short phrase), `points`.
- `[[criteria.ratings]]`: `id`, `description`, `points`.
- A `[module] items` entry references an assessment by its
  `.rubric.toml` filename (`{type="Assignment", id="example.rubric.toml"}`),
  resolved via the assessment's own `.tpa`.

## Not supported yet

Real per-criterion/per-rating identity against Canvas's own ids (see
"2. The rubric's criteria" above), and a points-possible drift check
between `[assignment] points_possible` and the criteria total --
nothing currently warns if the two disagree.
`dev/sample-assessment/example.rubric.toml` in the tent-pole checkout
is a complete, working example of everything above.
