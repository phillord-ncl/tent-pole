### -*- makefile -*-
### Pushes the markdown-feature test pages to a test Canvas instance.
### Mirrors the real course repos' make-inc/rules.inc pattern
### (pandoc --filter=canvas-filter -> tent-pole page push/dump). Also
### builds the same pages locally via code-include-filter (`make local`)
### -- no Canvas API access needed, just opens in a browser. See
### README.md for setup.

## Targets [dev] test_* from the global tent-pole.toml, not [general].
export TENT_POLE_USE_TEST_CONFIG=1

TENT_POLE=tent-pole
CANVAS_FILTER=canvas-filter
CODE_INCLUDE_FILTER=code-include-filter

MD_SOURCES=$(filter-out README.md,$(wildcard *.md))
TPP_FROM_MD=$(MD_SOURCES:%.md=%.tpp)

all: pages

## .tpf's needed before pandoc runs, since canvas-filter looks them up.
files: demo.py.tpf test-image.png.tpf test-video.mp4.tpf repl_demo.py.tpf crash_demo.py.tpf

## Not checked in -- generated so the repo carries no binary test data.
test-image.png: gen_test_image.py
	python3 $<

test-video.mp4:
	ffmpeg -f lavfi -i "testsrc=duration=2:size=320x240:rate=15" \
	       -f lavfi -i "sine=frequency=440:duration=2" \
	       -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest -y $@

demo.out: demo.py
	python3 $< > $@
	echo " " >> $@

## Interactive-shell transcript, mirrors rules.inc's %.stout rule.
%.stout: %.py
	cat $< | bin/python-shell > $@

## Script is meant to crash; "-" keeps make going despite the exit code.
%.crash: %.py
	- python3 $< 2> $@

%.tpf: %
	$(TENT_POLE) file push $<
	$(TENT_POLE) file dump $<

## Canvas returns media_entry_id = "maybe" right after upload until it
## decides whether to transcode; poll until it resolves to a real id.
test-video.mp4.tpf: test-video.mp4
	$(TENT_POLE) file push $<
	$(TENT_POLE) file dump $<
	while grep -q 'media_entry_id = "maybe"' $@; do \
		sleep 10; \
		$(TENT_POLE) file dump $<; \
	done

## .PRECIOUS: keep %.html around so check/verify have something real to
## hash -- otherwise make deletes it and a rebuild's fresh compile
## timestamp always looks like drift.
.PRECIOUS: %.html
%.html: %.md files demo.out repl_demo.stout crash_demo.crash
	pandoc --filter=$(CANVAS_FILTER) $< > $@

%.tpp: %.html
	$(TENT_POLE) page push $<
	$(TENT_POLE) page dump $<

pages: $(TPP_FROM_MD)

## Same pages, run through code-include-filter instead of canvas-filter
## -- no Canvas API access at all (no .tpf needed), so this can be
## opened straight in a browser to check the include=/output=/stout=/
## crash= syntax renders correctly through the other interpreter too,
## without a round trip to the sandbox course.
%.local.html: %.md demo.out repl_demo.stout crash_demo.crash test-image.png test-video.mp4
	pandoc --self-contained --filter=$(CODE_INCLUDE_FILTER) $< -o $@

local: $(MD_SOURCES:%.md=%.local.html)

## Once only -- re-running creates a second module of the same name.
create-module:
	$(TENT_POLE) module create "Markdown Feature Test"

reorder:
	$(TENT_POLE) module reorder

clean:
	rm -f *.html *.tpp *.tpf demo.out repl_demo.stout crash_demo.crash \
	      test-image.png test-video.mp4

.PHONY: all files pages local create-module reorder clean
