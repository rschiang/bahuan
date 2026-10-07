# Bahuan build: resolve → materialize → flags → nanoemoji per format → post-process.
# Run `uv sync` first; tools are taken from the project venv.
#
# Needs GNU make 4.x: parallel runs keep each step's log together with
# --output-sync, without which a failing job's error scrolls past unseen.
# macOS ships 3.81, so install Homebrew's make (`brew install make`) and build
# with `gmake`.
ifeq ($(filter output-sync,$(.FEATURES)),)
$(error GNU make 4.0+ required, found $(MAKE_VERSION); on macOS use `brew install make` and gmake)
endif
MAKEFLAGS += --output-sync=target

VENV ?= .venv
BIN := $(abspath $(VENV)/bin)
export PATH := $(BIN):$(PATH)
PYTHON := $(BIN)/python
STEAMER := $(BIN)/steamer
VERSION ?= 0.1

FORMATS := COLRv1 CBDT sbix SVG
CONFIG_colrv1 := Bahuan-COLRv1.ttf
CONFIG_cbdt := Bahuan-CBDT.ttf
CONFIG_sbix := Bahuan-sbix.ttf
CONFIG_svg := Bahuan-SVG.ttf
CONFIGS := colrv1 cbdt sbix svg
FONTS := $(foreach c,$(CONFIGS),build/out/$(CONFIG_$(c)))

STEAMER_SRC := $(wildcard steamer/*.py)

all: fonts web

fonts: $(FONTS)

# Upstream art: blob-less clone + one sparse worktree per era (several minutes).
sources/cache/.fetched: sources/eras.toml
	$(STEAMER) fetch
	touch $@

fetch: sources/cache/.fetched

selection/resolved.tsv: selection/selection.toml sources/eras.toml $(STEAMER_SRC)
	$(STEAMER) resolve

flags/out/.stamp: flags/waveflag.py $(wildcard flags/extra/*.svg) sources/emoji-test.txt sources/cache/.fetched
	$(PYTHON) flags/waveflag.py
	$(STEAMER) fetch waveflag
	touch $@

flags: flags/out/.stamp

# C reference for the waveflag golden test.
flags/waveflag: flags/waveflag.c
	$(CC) -std=c99 -O2 -Wall $< -o $@ `pkg-config --cflags --libs cairo` -lm

art/derived/.stamp: art/recipes.toml $(STEAMER_SRC) sources/cache/.fetched
	$(STEAMER) redraw
	touch $@

art/.stamp: selection/resolved.tsv flags/out/.stamp art/derived/.stamp $(STEAMER_SRC)
	$(STEAMER) materialize
	touch $@

build/config/.stamp: art/.stamp build/generate_configs.py
	$(PYTHON) build/generate_configs.py
	touch $@

# One nanoemoji run for every format, so the picosvg pass is shared.
build/work/.stamp: build/config/.stamp
	mkdir -p build/work
	cd build/config && $(BIN)/nanoemoji --build_dir=../work $(addsuffix .toml,$(CONFIGS))
	touch $@

build/out/%: build/work/.stamp build/postproc.py
	$(PYTHON) build/postproc.py --version $(VERSION) -o build/out build/work/$*

web: build/out/Bahuan-COLRv1.woff2

build/out/Bahuan-COLRv1.woff2: build/out/Bahuan-COLRv1.ttf build/web.py
	$(PYTHON) build/web.py $<

coverage: $(FONTS)
	$(PYTHON) build/check_coverage.py $(FONTS)

# fontbakery checks that apply to emoji fonts; fails on any FAIL.
QA_CHECKS := cmap/format_12 color_cpal_brightness empty_glyph_on_gid1_for_colrv0 \
	opentype/font_version opentype/name/empty_records opentype/postscript_name \
	opentype/family/equal_font_versions name/trailing_spaces name/no_copyright_on_description \
	os2_metrics_match_hhea unique_glyphnames sfnt_version

qa: $(FONTS)
	$(BIN)/fontbakery check-universal --succinct --error-code-on FAIL \
		$(foreach c,$(QA_CHECKS),-c $(c)) --html build/out/fontbakery.html $(FONTS)

check:
	$(STEAMER) lint
	$(STEAMER) resolve --check
	$(PYTHON) -m pytest -q

gallery: art/derived/.stamp
	$(STEAMER) gallery

clean:
	rm -rf build/work build/out build/config art/svg art/png art/derived art/.stamp flags/out gallery sheets

.PHONY: all fonts fetch flags web coverage qa check gallery clean
