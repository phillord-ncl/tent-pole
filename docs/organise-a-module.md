# Organise a module

A Canvas module's item list is normally driven declaratively from
`tent-pole.toml`, rather than built up with one-off commands.

## Declare the module and its contents

```toml
[module]
identifier = "Week 1"
items = [
  {id="intro"},
  {id="exercises", indent=1},
  {id="quiz-1.quiz.md", type="Quiz"},
]
```

```
tent-pole module reorder
```

`reorder` creates the module if it doesn't exist yet, then brings its
live item list in line with `items`: adding what's missing, editing
position/indent in place for anything already there (rather than
deleting and recreating it, which would reset student completion
state), and removing anything no longer listed. Safe to run
repeatedly -- with [start a new project](new-project.md)'s
`tent-pole build`, `tent-pole build reorder` does the same thing.

## Item types

- A page item's `id` is the page's `.md` filename (without extension)
  -- the same file `tent-pole page push` was given. Resolved via the
  page's *real* url, not the assumed filename-derived one, so it still
  works even if the page's url has drifted (see
  [write a page](write-a-page.md)).
- A quiz item's `id` is the `.quiz.md` filename, and needs `type="Quiz"`
  explicitly. The quiz must already have been pushed at least once
  (`tent-pole quiz push`) -- `reorder` resolves it via the quiz's own
  `.tpq` stamp file and refuses to guess at an unpushed quiz's id.
- `indent` (0 by default) nests an item under the previous one visually.

There's no sub-header entry type in `items` yet -- use
`tent-pole module addhead <module> <title> [indent]` directly for one
(see below).

## Checking what's there

```
tent-pole module data "Week 1"     # module metadata
tent-pole module list "Week 1"     # numbered live item list
tent-pole module dump              # the configured module's resolved
                                    # state as TOML, plus a content hash
```

`<module>` accepts a numeric id or a name (substring match, except
`reorder`/`dump` which always use the configured module from
`tent-pole.toml`/`-c`).

## One-off manual changes

For something outside the declarative `items` list -- a quick test, or
content that genuinely isn't page/quiz shaped:

```
tent-pole module create ["Week 2"]   # falls back to the configured
                                      # module if name is omitted;
                                      # no-op if it already exists
tent-pole module addpage "Week 1" some-page-url 1
tent-pole module addhead "Week 1" "Exercises"
tent-pole module addfile "Week 1" <file-id>
```

These don't update `tent-pole.toml`, so a later `reorder` won't know
about them -- prefer adding to `items` instead for anything meant to
persist.

## Deleting a module

```
tent-pole module delete "Week 1"
```

Prompts for confirmation; there's no undo.
