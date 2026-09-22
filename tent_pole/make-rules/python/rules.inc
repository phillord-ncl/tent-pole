### -*- makefile -*-
### Python-specific tent-pole Makefile rules -- capturing a script's
### output/traceback/REPL-transcript for embedding in course content.
### Include make-rules/rules.inc first; this builds on it, and relies
### on the leaf Makefile's own bootstrap having already set
### TENT_POLE_DIR -- not recomputed here.

## .PRECIOUS: these are prerequisites of %.html (a page's own %.tpd
## lists them for any include=d script using output=/stout=/crash=),
## not of a leaf Makefile's `all` directly -- exactly the mid-chain
## position GNU Make auto-deletes once the overall build succeeds,
## unless protected. See make-rules/rules.inc's own .PRECIOUS block
## for the full explanation and empirical confirmation.

## Run python with the same working directory as the python file.
.PRECIOUS: %.out
%.out: %.py
	@echo "  RUN      $<"
	$(Q)cd $(dir $<) && python3 $(notdir $<) > $(abspath $@)
	$(Q)echo " " >> $@

.PRECIOUS: %.crash
%.crash: %.py
	@echo "  CRASH    $<"
	- $(Q)cd $(dir $<) && python3 $(notdir $<) 2> $(abspath $@)

.PRECIOUS: %.stout
%.stout: %.py
	@echo "  REPL     $<"
	$(Q)cd $(dir $<) && cat $(notdir $<) | $(TENT_POLE_DIR)/bin/python-shell > $(abspath $@)

.PRECIOUS: %.test_out
%.test_out: %.py
	@echo "  TEST     $<"
	- $(Q)cd $(dir $<) && pytest $(notdir $<) > $(abspath $@)
	$(Q)echo " " >> $@

Makefile-generated: Makefile $(wildcard *.py)
	@echo "  GEN      $@"
	$(Q)python3 $(TENT_POLE_DIR)/bin/generate_makefile.py > Makefile-generated

clean-py:
	rm -f *.pyc *.out *.crash *.stout *.test_out Makefile-generated
