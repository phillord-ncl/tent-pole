# Sample course: R code-include test

A small standalone rig exercising R's `include=`/`chunk=`/`output=`/
`stout=`/`plot=`/`crash=` support, for manually reviewing a push
against a test Canvas instance (typically beta) by eye -- the same
role `markdown-features-1.md` plays for Python, see
`../sample-course-python/README.md`. Uses `demo.R`, real teaching
content (vector stats, two plots, a genuine R error), not canned
examples.

## Setup

Same as `../sample-course-python/README.md` -- `beta = true` here
reads `[dev] test_course_id`/`test_api_url`/`test_api_key` from your
own global `~/.config/tent-pole/tent-pole.toml`. Building also needs
R itself plus the `evaluate` package (`install.packages("evaluate")`)
-- see `docs/install.md`.

## Usage

With the venv active (`poetry shell`, or `poetry run` in front of
`tent-pole`):

```
tent-pole build pages   # builds + pushes r-demo.md
tent-pole build full    # builds it via code-include-filter instead --
                         # no Canvas access at all, just open
                         # r-demo.full.html in a browser
tent-pole build reorder # creates the "R Code Include Test" module if
                         # it doesn't exist yet, then (re-)populates it
```

Each section's own "Check:" text describes what should be visible on
Canvas (or in the browser, for `full`) -- refer to a section by its own
heading when reporting an issue.
