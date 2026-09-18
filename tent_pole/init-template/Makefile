{prelude}TENT_POLE ?= tent-pole
TENT_POLE_DIR := $(shell $(TENT_POLE) pkg-dir)
include $(TENT_POLE_DIR)/make-rules/rules.inc
include $(TENT_POLE_DIR)/make-rules/python/rules.inc

MD_SOURCES = $(filter-out %.quiz.md,$(wildcard *.md))
QUIZ_SOURCES = $(wildcard *.quiz.md)

include $(MD_SOURCES:%.md=%.tpd)   # auto-generated per-page dependencies

pages: $(MD_SOURCES:%.md=%.tpp)
quizzes: $(QUIZ_SOURCES:%.quiz.md=%.tpq)
full: $(MD_SOURCES:%.md=%.full.html)

.DEFAULT_GOAL := pages
.PHONY: pages quizzes full
