# Start a new project

A tent-pole project is a directory of markdown files plus a
`tent-pole.toml`, built with GNU Make and pushed to Canvas. This sets
one up from nothing.

## 1. Create the directory and configure the course

```
mkdir my-course && cd my-course
git init    # optional, but recommended -- content under version control
            # is one of the main points of tent-pole
```

```toml
# tent-pole.toml
[course]
id = "23212"   # numeric id, course code, or name -- see configure.md
```

Make sure your API key is set up first -- see [configure](configure.md).
If you're rehearsing against a sandbox rather than the real course,
also see its "point at a sandbox instead" section.

## 2. Bootstrap the Makefile

A leaf `Makefile` locates the installed tent-pole package and includes
its shared rules, rather than hand-writing push/dump/build recipes.
There's no `tent-pole init` command to generate this yet (a possible
future addition -- see `next_steps.md`), so for now, write it by hand
or copy `dev/sample-course/Makefile` from the tent-pole checkout and
strip its sample-specific bits (image/video generation, `clean`):

```makefile
TENT_POLE ?= tent-pole
TENT_POLE_DIR := $(shell $(TENT_POLE) pkg-dir)
include $(TENT_POLE_DIR)/make-rules/rules.inc
include $(TENT_POLE_DIR)/make-rules/python/rules.inc

MD_SOURCES = $(filter-out %.quiz.md,$(wildcard *.md))
QUIZ_SOURCES = $(wildcard *.quiz.md)

include $(MD_SOURCES:%.md=%.tpd)   # auto-generated per-page dependencies

pages: $(MD_SOURCES:%.md=%.tpp)
quizzes: $(QUIZ_SOURCES:%.quiz.md=%.tpq)
full: $(MD_SOURCES:%.md=%.full.html)

.DEFAULT_GOAL := pages
.PHONY: pages quizzes full
```

`rules.inc` builds your markdown pages and quizzes and gets them onto
Canvas -- pushing/dumping pages, files, and quizzes, and generating the
per-page dependencies that make `make pages` pick up everything a page
actually references. `python/rules.inc` adds support for including
Python source and its captured output in a page or quiz (see
[write a page](write-a-page.md)). `dev/sample-course/Makefile` in the
tent-pole checkout is a complete working example of this pattern;
adapt from there rather than from scratch if in doubt.

The Makefile is otherwise a normal Makefile -- add whatever else your
course needs on top, e.g. a `slides.html` target running pandoc with a
Slidy/reveal.js template, or a `handbook.pdf` target assembling several
pages into a single document via eisvogel. Only project-specific bits
like these belong in your own Makefile; the shared rules above cover
what every project needs regardless of subject.

See `docs/migration.md` if you're instead bringing an *existing*
project's Makefile up to date with the current shared rules, rather
than starting fresh.

## 3. Write and push your first page

```
echo '# Hello' > hello.md
make pages
```

builds `hello.md` through pandoc + `canvas-filter` and pushes it. See
[write a page](write-a-page.md) for what the markdown can contain.

## 4. Put it in a module

```toml
# tent-pole.toml, appended
[module]
identifier = "Week 1"
items = [
  {id="hello"},
]
```

```
make reorder
```

See [organise a module](organise-a-module.md) for indenting, sub-headers,
and quizzes in the item list.

## 5. Add a quiz (optional)

See [write a quiz](write-a-quiz.md) once you have at least one page in
place -- the same `make` pattern above already builds `.quiz.md`
files via `QUIZ_SOURCES`.
