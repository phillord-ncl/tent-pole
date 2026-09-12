### -*- makefile -*-
### Python-specific tent-pole Makefile rules -- capturing a script's
### output/traceback/REPL-transcript for embedding in course content.
### Include make-rules/rules.inc first; this builds on it, and relies
### on the leaf Makefile's own bootstrap having already set
### TENT_POLE_DIR -- not recomputed here.

%.out: %.py
	python3 $< > $@
	echo " " >> $@

%.crash: %.py
	- python3 $< 2> $@

%.stout: %.py
	cat $< | $(TENT_POLE_DIR)/bin/python-shell > $@

%.test_out: %.py
	- pytest $< > $@
	echo " " >> $@

Makefile-generated: Makefile $(wildcard *.py)
	python3 $(TENT_POLE_DIR)/bin/generate_makefile.py > Makefile-generated

clean-py:
	rm -f *.pyc *.out *.crash *.stout *.test_out Makefile-generated
