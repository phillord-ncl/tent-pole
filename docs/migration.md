# Migration

## 0.2.0

Steps to migrate a course repo from a previous tent-pole version onto
this one:

1. Locate the installed package with `tent-pole pkg-dir` instead of
   hardcoding a path to a tent-pole checkout. Bootstrap it once, at
   the top of the repo's shared Makefile fragment:

   ```makefile
   TENT_POLE ?= tent-pole
   TENT_POLE_DIR := $(shell $(TENT_POLE) pkg-dir)
   include $(TENT_POLE_DIR)/make-rules/rules.inc
   include $(TENT_POLE_DIR)/make-rules/python/rules.inc
   ```

2. Remove any local per-extension push/dump rule (a `PUSH_template`/
   `PUSH_EXTS`-style macro, or individual `%.ext.tpf: %.ext` rules).
   `rules.inc` provides one generic `%.tpf: %` rule covering every
   extension, using `file dump --wait`.

3. Remove any local `%.out`/`%.crash`/`%.stout`/`%.test_out` rules and
   a local `Makefile-generated`/dependency-generator script.
   `python/rules.inc` provides these, backed by
   `tent_pole/bin/python-shell` and `tent_pole/bin/generate_makefile.py`.
   Delete a repo's own copies once nothing references them directly
   (check for direct references by relative path first, not just
   inclusion through the shared rules).

4. Remove a separate `create`/`create-module` step. `module reorder`
   creates the module itself if it does not exist yet.

5. Keep anything genuinely project-specific — course-authoring house
   style such as Slidy/eisvogel templates, or a project's own
   resources/pandoc paths — in the repo's own Makefile fragment. Only
   the generic parts move to tent-pole.

6. Optionally, adopt auto-generated per-page dependencies in place of
   hand-listed image/include prerequisites:

   ```makefile
   MD_SOURCES=$(wildcard *.md)
   include $(MD_SOURCES:%.md=%.tpd)
   ```

   This tracks only what a page actually references via `include=`, an
   image, or a local-file link — a page-to-page link is never treated
   as a dependency, and a file pushed only for its own sake, never
   referenced from any page, still needs its own explicit rule.
