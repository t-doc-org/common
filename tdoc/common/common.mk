# Copyright 2024 Caroline Blank <caro@c-space.org>
# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

# Configuration.
COLOR ?= 1
SPHINX_OPTS ?= --jobs=auto --fail-on-warning
SPHINX_BUILD ?= sphinx-build
SOURCE ?= docs
BUILD ?= docs/_build

# ANSI escape codes.
_V := $(if $(VERBOSE:0=),,@)
_ANSI = $(if $(COLOR:0=),\e[$(1)m)
_NORM := $(call _ANSI,39)
_BLACK := $(call _ANSI,30)
_RED := $(call _ANSI,31)
_GREEN := $(call _ANSI,32)
_YELLOW := $(call _ANSI,33)
_BLUE := $(call _ANSI,34)
_MAGENTA := $(call _ANSI,35)
_CYAN := $(call _ANSI,36)
_GREY := $(call _ANSI,37)
_DGREY := $(call _ANSI,90)
_LRED := $(call _ANSI,91)
_LGREEN := $(call _ANSI,92)
_LYELLOW := $(call _ANSI,93)
_LBLUE := $(call _ANSI,94)
_LMAGENTA := $(call _ANSI,95)
_LCYAN := $(call _ANSI,96)
_WHITE := $(call _ANSI,97)

.PHONY: default
default: help

.PHONY: help
help:
	$(_V)echo -e "$(_WHITE)Make targets:$(_NORM)"
	$(_V)echo -e "  $(_LBLUE)serve$(_NORM): Build the $(_LBLUE)html$(_NORM) target, then serve the result on http://localhost:8000"
	$(_V)echo -e
	$(_V)PYTHONPATH="$(PYTHONPATH)" $(SPHINX_BUILD) -M help \
		"$(SOURCE)" "$(BUILD)" $(SPHINX_OPTS) $(O)

.PHONY: serve
serve: html
	$(_V)echo -e "$(_WHITE)Serving:$(_NORM) $(_LBLUE)http://localhost:8000$(_NORM)"
	$(_V)PYTHONPATH="$(PYTHONPATH)" $(PYTHON) -m http.server \
		--bind=localhost --directory="$(BUILD)/html"

%:
	$(_V)PYTHONPATH="$(PYTHONPATH)" $(SPHINX_BUILD) -M $@ \
		"$(SOURCE)" "$(BUILD)" $(SPHINX_OPTS) $(O)
