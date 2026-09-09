### -*- makefile -*-
### Standalone rig for pushing the markdown-feature test pages to beta.
### Mirrors the real course repos' make-inc/rules.inc pattern (pandoc
### --filter=canvas-filter -> tent-pole page push/dump, file push/dump
### for anything a page references) but self-contained, since this lives
### in tent-pole's own dev/ area rather than a course repo. See README.md.

## Every tent-pole/canvas-filter invocation below targets [dev]
## test_course_id/test_api_url/test_api_key from your own global
## tent-pole.toml (~/.config/tent-pole/tent-pole.toml), never [general]/
## [course]/production -- see README.md. Nothing target- or
## credential-specific lives in this directory at all.
export TENT_POLE_USE_TEST_CONFIG=1

TENT_POLE=tent-pole
CANVAS_FILTER=canvas-filter

## Excludes README.md -- it documents the fixture, it isn't a Canvas page.
MD_SOURCES=$(filter-out README.md,$(wildcard *.md))
TPP_FROM_MD=$(MD_SOURCES:%.md=%.tpp)

all: pages

## Files referenced from inside the pages (include=/image/link) need to
## exist on Canvas -- with a .tpf recording their file id -- before
## pandoc runs the filter, since canvas-filter looks up e.g.
## test-image.png.tpf while building the page HTML.
files: demo.py.tpf test-image.png.tpf test-video.mp4.tpf repl_demo.py.tpf crash_demo.py.tpf

## Generated rather than checked in, so the repo doesn't carry binary
## test assets -- see gen_test_image.py and README.md.
test-image.png: gen_test_image.py
	python3 $<

test-video.mp4:
	ffmpeg -f lavfi -i "testsrc=duration=2:size=320x240:rate=15" \
	       -f lavfi -i "sine=frequency=440:duration=2" \
	       -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest -y $@

demo.out: demo.py
	python3 $< > $@
	echo " " >> $@

## Mirrors rules.inc's %.stout rule: feeds the script to bin/python-shell
## line by line, capturing it as an interactive REPL transcript (>>> / ...
## prompts) rather than the script's own stdout.
%.stout: %.py
	cat $< | bin/python-shell > $@

## Mirrors rules.inc's %.crash rule: the leading "-" tells make to ignore
## the script's non-zero exit status (it's *supposed* to crash), capturing
## stderr as the traceback to display.
%.crash: %.py
	- python3 $< 2> $@

%.tpf: %
	$(TENT_POLE) file push $<
	$(TENT_POLE) file dump $<

## mp4 needs its own rule: right after upload, Canvas hasn't decided yet
## whether the file becomes a media object, and the Files API returns the
## literal string "maybe" for media_entry_id in the meantime (confirmed
## live, 2026-09-08) -- not an error, just not ready. A dump taken then
## bakes "maybe" into the .tpf, which link_filter would embed verbatim as
## an invalid data-media-id. Poll until it resolves to a real id instead.
test-video.mp4.tpf: test-video.mp4
	$(TENT_POLE) file push $<
	$(TENT_POLE) file dump $<
	while grep -q 'media_entry_id = "maybe"' $@; do \
		echo "media_entry_id still \"maybe\", waiting on Canvas..."; \
		sleep 10; \
		$(TENT_POLE) file dump $<; \
	done

%.html: %.md files demo.out repl_demo.stout crash_demo.crash
	pandoc --filter=$(CANVAS_FILTER) $< > $@

%.tpp: %.html
	$(TENT_POLE) page push $<
	$(TENT_POLE) page dump $<

pages: $(TPP_FROM_MD)

## Run once, before the first `make reorder` -- creates the module itself.
## Re-running this creates a second module of the same name rather than
## reusing the first, so don't add it to `all`.
create-module:
	$(TENT_POLE) module create "Markdown Feature Test"

## Safe to re-run: replaces the module's item list wholesale from
## tent-pole.toml's [module] items every time.
reorder:
	$(TENT_POLE) module reorder

clean:
	rm -f *.html *.tpp *.tpf demo.out repl_demo.stout crash_demo.crash \
	      test-image.png test-video.mp4

.PHONY: all files pages create-module reorder clean
