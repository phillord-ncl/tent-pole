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

## TENT_POLE is NOT defaulted here -- the leaf Makefile's own bootstrap
## must already have set it, to find this very file in the first
## place. Unlike TENT_POLE_DIR above, MAKEFILE_LIST cannot recover
## this: it is a command name, not a path.
CANVAS_FILTER ?= canvas-filter
CODE_INCLUDE_FILTER ?= code-include-filter

%.tpf: %
	$(TENT_POLE) file push $<
	$(TENT_POLE) file dump --wait $<

.PRECIOUS: %.html
%.html: %.md
	pandoc --filter=$(CANVAS_FILTER) $< > $@

%.tpp: %.html
	$(TENT_POLE) page push $<
	$(TENT_POLE) page dump $<

## Self-contained, viewable outside Canvas. Not called ".local.html" --
## the point isn't "local" vs "remote", it's that this is a full,
## standalone document, unlike canvas-filter's bare fragment meant for
## Canvas's own page wrapper.
%.full.html: %.md
	pandoc --self-contained --filter=$(CODE_INCLUDE_FILTER) $< -o $@

## No separate create-module target -- reorder gets-or-creates the
## module itself, so this is the only step ever needed, even on a
## completely fresh course.
tent-pole.toml.tpm: tent-pole.toml
	$(TENT_POLE) module reorder
	$(TENT_POLE) module dump > $@

.PHONY: reorder
reorder: tent-pole.toml.tpm

clean-tp:
	rm -f *.html *.tpp *.tpf
