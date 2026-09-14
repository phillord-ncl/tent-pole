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
## true (as it isn't for README.md), this can be filtered or explicit.
## .quiz.md files are also *.md as far as the shell glob is concerned,
## so they're filtered out here too -- QUIZ_SOURCES below is their own
## separate list.
MD_SOURCES=$(filter-out README.md,$(filter-out %.quiz.md,$(wildcard *.md)))

## Load the dependencies for these markdown files. These are
## automatically generated (via rules.inc's %.tpd: %.md), so every
## image/include=/link a page actually uses becomes a real
## prerequisite of its %.html/%.full.html -- no more hand-listing
## them below, and no more files:/create-module-style manual steps.
include $(MD_SOURCES:%.md=%.tpd)

## The quiz samples for tent-pole issue #14 -- no .tpd dependency
## generation exists for .quiz.md yet (see the plan's follow-up list),
## so their include=d files are listed explicitly below instead.
QUIZ_SOURCES=$(wildcard *.quiz.md)

question-types-quiz.tpq: demo.py.tpf quiz_crash_demo.py.tpf demo.out quiz_crash_demo.crash

all: pages quizzes

## These are the pages that will end up on canvas.
pages: $(MD_SOURCES:%.md=%.tpp)

## Full pages are self-contained local versions of files which are
## rather quicker to interact with than canvas and work offline.
full: $(MD_SOURCES:%.md=%.full.html)

## The quizzes that will end up on canvas.
quizzes: $(QUIZ_SOURCES:%.quiz.md=%.tpq)

## Self-contained local previews of the quizzes, same idea as `full`
## above but for .quiz.md sources.
quiz-full: $(QUIZ_SOURCES:%.quiz.md=%.quiz.full.html)

## The use of make means we can use any tools that we like to generate
## our files for later includsion. Not checked in -- generated so the
## repo carries no binary test data.
test-image.png: gen_test_image.py
	python3 $<

test-video.mp4:
	ffmpeg -f lavfi -i "testsrc=duration=2:size=320x240:rate=15" \
	       -f lavfi -i "sine=frequency=440:duration=2" \
	       -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest -y $@

clean: clean-tp clean-py
	rm -f test-image.png test-video.mp4

## It is useful to set a default goal as there are many included
## files.
.DEFAULT_GOAL := all

.PHONY: all pages full quizzes quiz-full clean
