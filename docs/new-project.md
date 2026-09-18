# Start a new project

A tent-pole project is a directory of markdown files plus a
`tent-pole.toml`, built with GNU Make and pushed to Canvas.

You should ensure your API key is [configured](configure.md) first
before you run this.

## 1. Scaffold

```
mkdir my-course && cd my-course
tent-pole init
```

This creates a `Makefile`, `tent-pole.toml`, and a starter `hello.md`, and
runs `git init` -- content under version control is one of the main
points of tent-pole.

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

To run the build and push the pages to Canvas, we use two make commands.

```
make pages
make reorder
```

`make pages` builds `hello.md` into HTML which is then pushed to
Canvas. See [write a page](write-a-page.md) for what the markdown can
contain. `make reorder` creates the module if needed, and
[organises](organise-a-module.md) the pages with in it.

The generated `Makefile` contains specific support for `tent-pole` but
is otherwise normal. You can add whatever else you course needs to it.

## `init` options

- `--no-git` -- don't run `git init`.
- `--tent-pole-dev` -- for tent-pole development this runs `tent-pole`
  directly from source using `poetry` avoiding the need for continual
  re-installation.
