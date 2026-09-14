# Write a quiz

A `.quiz.md` file authors a Canvas quiz the same way an ordinary `.md`
file authors a page -- front matter, headers, checkbox lists, code
blocks -- rather than a separate quiz-specific syntax. This walks
through building one up from nothing; see
[docs/quiz-markdown.md](quiz-markdown.md) for the full field-by-field
reference once the shape is familiar.

## 1. Front matter and one question

````markdown
---
title: "Week 1 quiz"
quiz_type: practice_quiz
---

### What does this print? {.question points="1"}

```python
print("hello")
```

- [x] hello
- [ ] "hello"
- [ ] print(hello)
````

Front matter maps near-verbatim to quiz-level settings (`title`,
`quiz_type`, `allowed_attempts`, `scoring_policy`, ...). Body text
before the first header becomes the quiz description. A header
carrying `.question` is one question; its own text becomes the
question name, everything under it (including the code block) becomes
the question text.

## 2. Check it before pushing

```
tent-pole quiz push --dry-run week-1.quiz.md
```

parses the file and prints the structure -- no network access, no
Canvas needed. Fix anything that looks wrong here first.

## 3. Push it

```
tent-pole quiz push week-1.quiz.md
```

creates or updates the quiz. **Every push deletes and recreates every
question and group** -- nothing in the markdown gives a question a
stable identity across edits, so this is a full replace, not a diff.
Tent-pole refuses to push over a quiz that's published or has any
submissions, unless you pass `--force` (which would destroy
submission-linked data) -- deliberately, since accidentally clobbering
real student answers is the failure mode this guards against.

## 4. Answer types

A checkbox list right under a question becomes its answers -- no
`type=` needed, it's inferred:

- Exactly one `[x]` -> multiple choice.
- More than one `[x]` -> multiple answers (pick all that apply).
- No checkbox list at all -> essay/free text -- but then `type="essay"`
  must be written explicitly, since there's nothing to infer from.

```markdown
### Pick all prime numbers {.question points="1"}

- [x] 2
- [x] 3
- [ ] 4
- [x] 5
```

## 5. Group questions together

A header one level shallower than its questions, carrying `.group`:

```markdown
## Warm-up questions {.group pick="2" points="1"}

### Question A {.question}
...

### Question B {.question}
...

### Question C {.question}
...
```

`pick="2"` -> Canvas picks 2 of the 3 at random per attempt; `points`
is each picked question's worth. A group with zero questions under it
is still valid -- useful as a placeholder whose `pick`/`points` count
toward the quiz total already, before its real questions are written.

## 6. Put it in a module

Once pushed at least once, reference it from `tent-pole.toml` the same
way a page is referenced -- see
[organise a module](organise-a-module.md#item-types).

## 7. Preview without Canvas

```
make quiz-full   # or: pandoc --self-contained --filter=code-include-filter week-1.quiz.md -o week-1.quiz.full.html
```

builds a standalone HTML file to eyeball in a browser -- the same idea
as a page's own local preview.

## Not supported yet

Matching, numerical, fill-in-multiple-blanks, and question-bank
question types. `dev/sample-course/question-types-quiz.quiz.md` and
`question-groups-quiz.quiz.md` in the tent-pole checkout are complete,
working examples of everything above.
