### -*- makefile -*-
### Generic tent-pole Makefile rules: any tent-pole project can
### `include` this, Python or not. See make-rules/python/rules.inc for
### the Python-specific layer.

## An included Makefile can find its own location the same way Python
## code finds __file__: the last-appended entry in MAKEFILE_LIST, read
## before anything else gets included below. Deriving TENT_POLE_DIR
## this way makes this file self-contained regardless of how it was
## found, rather than trusting the includer to have already set it
## correctly.
TENT_POLE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))..)

## GNU Make's default is to leave a target file in place after its own
## recipe fails. Every rule here writes its target via shell
## redirection, which creates the file before the command runs, so a
## transient failure can leave a stale, empty file that a later run
## then treats as up to date.
.DELETE_ON_ERROR:

## TENT_POLE is NOT defaulted here -- the leaf Makefile's own bootstrap
## must already have set it, to find this very file in the first
## place. Unlike TENT_POLE_DIR above, MAKEFILE_LIST cannot recover
## this: it is a command name, not a path.
CANVAS_FILTER ?= canvas-filter
CODE_INCLUDE_FILTER ?= code-include-filter
INCLUDE_DEPS_FILTER ?= include-deps-filter

## Quiet by default (a short "  VERB     target" line instead of the
## full command), same convention as Automake's `make V=1`: V=1 shows
## the full command too, in addition to the short line rather than
## instead of it -- full command visibility (exact paths/flags) is
## genuinely needed for debugging, not just a fallback for distrust.
## $(Q) must appear immediately after any leading -/@/+ recipe-prefix
## character, never before it -- make checks those against the
## already-macro-expanded recipe text, not literally the first
## character of what's written here, but only once, so a second
## leading modifier appearing after expansion is never re-checked.
V ?= 0
ifeq ($(V),1)
Q =
else
Q = @
endif

## Auto-generated Make dependencies for a single .md file -- the
## include=/output=/stout=/crash= attributes on its code blocks, plus
## any local image/file it embeds or links to. Named after its own
## concrete stem, not the literal pattern % -- a second declaration of
## the same pattern never merges with %.html/%.full.html above.
## Deliberately not a co-target of %.html/%.tpf the way a C header's
## %.d is a co-target of %.o: that only helps when a referenced file's
## own content can change the dependency list, which never happens
## here, since this only parses the .md file's own syntax. A leaf
## Makefile's own `include $(MD_SOURCES:%.md=%.tpd)` (MD_SOURCES is
## per-project, so that line cannot live here) is what pulls these in.
%.tpd: %.md
	@echo "  DEPS     $<"
	$(Q)$(INCLUDE_DEPS_FILTER) $< > $@

%.tpf: %
	@echo "  PUSH     $<"
	$(Q)$(TENT_POLE) file push $<
	@echo "  DUMP     $<"
	$(Q)$(TENT_POLE) file dump $<

## Media needs --wait: Canvas returns a placeholder media_entry_id
## until transcoding finishes, and canvas_filter's own mp4 handling
## (an <iframe data-media-id=...>) needs the real one, not "maybe".
## A more specific pattern (longer stem match) than the generic
## %.tpf: % above, so make prefers this one for an actual .mp4 --
## everything else keeps the plain dump, which was always a no-op for
## a non-media file anyway (media_entry_id is never "maybe" for one).
%.mp4.tpf: %.mp4
	@echo "  PUSH     $<"
	$(Q)$(TENT_POLE) file push $<
	@echo "  DUMP     $<"
	$(Q)$(TENT_POLE) file dump --wait $<

.PRECIOUS: %.html
%.html: %.md
	@echo "  HTML     $<"
	$(Q)pandoc --filter=$(CANVAS_FILTER) $< > $@

%.tpp: %.html
	@echo "  PUSH     $<"
	$(Q)$(TENT_POLE) page push $<
	@echo "  DUMP     $<"
	$(Q)$(TENT_POLE) page dump $<

## Self-contained, viewable outside Canvas. Not called ".local.html" --
## the point isn't "local" vs "remote", it's that this is a full,
## standalone document, unlike canvas-filter's bare fragment meant for
## Canvas's own page wrapper.
%.full.html: %.md
	@echo "  FULL     $<"
	$(Q)pandoc --embed-resources --standalone --filter=$(CODE_INCLUDE_FILTER) $< -o $@

## A .quiz.md file is authored quite differently from an ordinary
## page (see tent-pole issue #14), but is still a plain `*.md` file as
## far as a shell glob is concerned -- a leaf Makefile's own
## `MD_SOURCES = $(wildcard *.md)` will happily sweep up a `.quiz.md`
## file too, pushing it as an ordinary page. A leaf Makefile mixing
## both content types in one directory needs to filter its own
## MD_SOURCES (e.g. `$(filter-out %.quiz.md,$(wildcard *.md))`)
## alongside its own `QUIZ_SOURCES = $(wildcard *.quiz.md)` -- neither
## variable is declared here, same as MD_SOURCES never has been.
##
## push already both creates-or-updates and writes its own stamp, so
## unlike a page there's no separate dump step needed here.
%.tpq: %.quiz.md
	@echo "  QUIZ     $<"
	$(Q)$(TENT_POLE) quiz push $<

## More specific (shorter stem) than %.full.html: %.md above, so make
## prefers this one for an actual .quiz.md file -- same precedent as
## %.mp4.tpf: %.mp4 above. Reuses %.full.html's own recipe body
## verbatim: plain pandoc already renders a .quiz.md file's headers/
## checkboxes/code correctly for a human preview, the same way it does
## for an ordinary page -- no new preview-side code needed.
%.quiz.full.html: %.quiz.md
	@echo "  FULL     $<"
	$(Q)pandoc --embed-resources --standalone --filter=$(CODE_INCLUDE_FILTER) $< -o $@

## No separate create-module target -- reorder gets-or-creates the
## module itself, so this is the only step ever needed, even on a
## completely fresh course.
tent-pole.toml.tpm: tent-pole.toml
	@echo "  REORDER  $<"
	$(Q)$(TENT_POLE) module reorder
	@echo "  DUMP     $<"
	$(Q)$(TENT_POLE) module dump > $@

.PHONY: reorder
reorder: tent-pole.toml.tpm

clean-tp:
	rm -f *.html *.tpp *.tpf *.tpd *.tpm *.tpq
