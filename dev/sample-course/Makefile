### -*- makefile -*-
### Pushes the markdown-feature test pages to a test Canvas instance.
### Mirrors the real course repos' make-inc/rules.inc pattern
### (pandoc --filter=canvas-filter -> tent-pole page push/dump). Also
### builds the same pages locally via code-include-filter (`make full`)
### -- no Canvas API access needed, just opens in a browser. See
### README.md for setup.

## As this is a sample file, use the test configuration options, which
## will usually mean the beta website.
export TENT_POLE_USE_TEST_CONFIG=1

## We need access the tent-pole executable. We assume this is directly
## through the system path for an installed tent-pole. During
## development this can point to a script that uses poetry run
TENT_POLE ?= tent-pole
TENT_POLE_DIR := $(shell $(TENT_POLE) pkg-dir)

## Include the standard rules for generating HTML and pushing this to
## canvas.
include $(TENT_POLE_DIR)/make-rules/rules.inc

## Include the standard rules for dealing with python files which will
## run them and allow incorporate of standard output or errors onto
## the canvas page.
include $(TENT_POLE_DIR)/make-rules/python/rules.inc

## Use anything with a *md extension as a source file. If this is not
## true (as it isn't for README.md), this can be filtered or explicit
MD_SOURCES=$(filter-out README.md,$(wildcard *.md))

## TODO (feature/include-deps-filter, step 5): once the dependency-
## extraction filter exists, `include $(MD_SOURCES:%.md=%.tpd)` here
## replaces `files:` and the two extra-prerequisite lines below with
## per-page generated dependencies -- see the plan.

all: pages

## These are the pages that will end up on canvas.
pages: $(MD_SOURCES:%.md=%.tpp)

## Full pages are self-contained local versions of files which are
## rather quicker to interact with than canvas and work offline.
full: $(MD_SOURCES:%.md=%.full.html)

## .tpf's needed before pandoc runs, since canvas-filter looks them up.
files: demo.py.tpf test-image.png.tpf test-video.mp4.tpf repl_demo.py.tpf crash_demo.py.tpf

## The use of make means we can use any tools that we like to generate
## our files for later includsion. Not checked in -- generated so the
## repo carries no binary test data.
test-image.png: gen_test_image.py
	python3 $<

test-video.mp4:
	ffmpeg -f lavfi -i "testsrc=duration=2:size=320x240:rate=15" \
	       -f lavfi -i "sine=frequency=440:duration=2" \
	       -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest -y $@

## Extra prerequisites for the concrete .html/.full.html filenames --
## Make merges these with rules.inc's %.html/%.full.html pattern rules
## (which supply the actual recipe), but *only* because these name the
## concrete files, not the pattern itself: a second %.html: ... stanza
## would silently never be consulted (verified directly -- Make picks
## one pattern rule per pattern, it doesn't merge across declarations
## of the same one).
$(MD_SOURCES:%.md=%.html): files demo.out repl_demo.stout crash_demo.crash
$(MD_SOURCES:%.md=%.full.html): demo.out repl_demo.stout crash_demo.crash test-image.png test-video.mp4

## Once only -- re-running creates a second module of the same name.
## TODO (feature/module-reorder, step 4): once reorder() gets-or-
## creates the module itself, this target goes away entirely.
create-module:
	$(TENT_POLE) module create "Markdown Feature Test"

clean: clean-tp clean-py
	rm -f test-image.png test-video.mp4

## It is useful to set a default goal as there are many included
## files.
.DEFAULT_GOAL := all

.PHONY: all files pages full create-module clean
