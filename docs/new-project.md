# Start a new project

A tent-pole project is a directory of markdown files plus a
`tent-pole.toml`, built with `tent-pole build` and pushed to Canvas.

You should ensure your API key is [configured](configure.md) first
before you run this.

## 1. Scaffold

```
mkdir my-course && cd my-course
tent-pole init
```

This creates a `tent-pole.toml` and a starter `hello.md`, and runs
`git init` -- content under version control is one of the main points
of tent-pole. No build file is scaffolded: `tent-pole build` already
knows how to build a plain directory of markdown pages on its own,
with nothing local to configure.

## 2. Configure the course and module

`tent-pole init` also creates a `tent-pole.toml` file which describes
how the markdown files will be pushed to Canvas. You will need to
alter the course ID to a course you control on Canvas.

```toml
# tent-pole.toml
[course]
id = "COURSE_NAME"   # numeric id, course code, or name -- see configure.md

[module]
identifier = "Hello World Module"
items = [
  {id="hello"},
]
```

## 3. Build and push

To run the build and push the pages to Canvas, we use two `tent-pole
build` commands.

```
tent-pole build
tent-pole build reorder
```

`tent-pole build` (its default goal, `pages`) builds `hello.md` into
HTML which is then pushed to Canvas. See [write a page](write-a-page.md)
for what the markdown can contain. `tent-pole build reorder` creates
the module if needed, and [organises](organise-a-module.md) the pages
within it.

A project needing rules beyond the built-in ones (a second markup
language's own compile step, say) adds its own `dodo.py` doing `from
tent_pole.doit_rules import *` to keep everything above, then defines
its own extra tasks alongside -- see
[include-code.md](include-code.md) for CSC1034's own pandoc rules as
a worked example.

## `init` options

- `--no-git` -- don't run `git init`.

Already have content on Canvas rather than starting from scratch? See
[import an existing course](import-a-course.md) instead.
