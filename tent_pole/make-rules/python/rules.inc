### -*- makefile -*-
### Python-specific tent-pole Makefile rules -- capturing a script's
### output/traceback/REPL-transcript for embedding in course content.
### Include make-rules/rules.inc first; this builds on it, and relies
### on the leaf Makefile's own bootstrap having already set
### TENT_POLE_DIR -- not recomputed here.

## Run python with the same working directory as the python file.
%.out: %.py
	cd $(dir $<) && python3 $(notdir $<) > $(abspath $@)
	echo " " >> $@

%.crash: %.py
	- cd $(dir $<) && python3 $(notdir $<) 2> $(abspath $@)

%.stout: %.py
	cd $(dir $<) && cat $(notdir $<) | $(TENT_POLE_DIR)/bin/python-shell > $(abspath $@)

%.test_out: %.py
	- cd $(dir $<) && pytest $(notdir $<) > $(abspath $@)
	echo " " >> $@

Makefile-generated: Makefile $(wildcard *.py)
	python3 $(TENT_POLE_DIR)/bin/generate_makefile.py > Makefile-generated

clean-py:
	rm -f *.pyc *.out *.crash *.stout *.test_out Makefile-generated
