# SPDX-License-Identifier: GPL-3.0-or-later
"""Stress tests for the Firefox bridge's page-CONTENT dimming CSS.

``services/firefox-extension/background.js::makeCss`` is the single lever on
how nightpanel dims page media. It generates user-origin CSS injected via
``tabs.insertCSS`` (see the adapter/orchestrator). It previously had ZERO
automated coverage — only the e2e marionette matrix exercised it — which is
how a stray backtick in a CSS comment (terminating the JS template literal)
could have shipped silently.

These tests render the REAL CSS by evaluating ``makeCss`` in node, then assert
two things the marionette matrix can't pin down deterministically:

  1. The dimming *tiers* across a brightness sweep — decorative imagery
     (``img``/``picture``/``embed``/``object``) heavy; functional ``canvas``
     surfaces (spreadsheet grids) gentle; ``video`` and video-player embeds
     untouched; general ``iframe`` still dimmed.
  2. The cascade *outcome* per element. Every filter rule is user-origin
     ``!important``, so the winner is decided by (specificity, source order).
     We model that resolution for representative elements — the property that
     determines whether a YouTube embed stays crisp and a Sheets grid stays
     legible. Substring presence is necessary but NOT sufficient: an exclusion
     rule that appears *before* the broad rule, or under-specifies, would lose
     the cascade while still "being present".

The companion userChrome.css surface is covered by test_firefox_chrome.py.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

_BG_JS = (
    Path(__file__).parents[2]
    / "src"
    / "nightpanel"
    / "services"
    / "firefox-extension"
    / "background.js"
)

# A node program that loads background.js, neuters the boot side effects
# (connect()/onInstalled), and prints makeCss(b) for each brightness passed on
# argv, separated by a sentinel — one node spawn renders an arbitrarily large
# sweep. Reading the real file (not a copy of the CSS) means these tests fail
# the moment the template stops parsing or the tiers change.
_SENTINEL = "\n===NPCSS===\n"
_NODE_RENDER = r"""
const fs = require('fs');
const argv = process.argv.slice(2);
const path = argv[0];
let src = fs.readFileSync(path, 'utf8').replace('connect();', '/* test: boot disabled */');
// browser.* is a chainable no-op so the top-level onInstalled.addListener and
// any incidental member access during load resolve without a real WebExt env.
const browser = new Proxy(function () {}, { get: () => browser, apply: () => undefined });
const makeCss = new Function('browser', 'console', 'Date', 'Math', src + '\n;return makeCss;')(
    browser, console, Date, Math,
);
const out = argv.slice(1).map((b) => makeCss(parseFloat(b)));
process.stdout.write(out.join('\n===NPCSS===\n'));
"""

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="node required to evaluate background.js"
)


# ── rendering ────────────────────────────────────────────────────────────────


def render_many(brightnesses) -> list[str]:
    """Evaluate makeCss(b) for each brightness in ONE node spawn."""
    brightnesses = list(brightnesses)
    proc = subprocess.run(
        ["node", "-", str(_BG_JS), *(str(b) for b in brightnesses)],
        input=_NODE_RENDER,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"node render failed: {proc.stderr}"
    parts = proc.stdout.split(_SENTINEL)
    assert len(parts) == len(brightnesses), "render count mismatch"
    return parts


def render_css(brightness: float) -> str:
    """Evaluate makeCss(brightness) in node and return the generated CSS."""
    return render_many([brightness])[0]


# ── a minimal, faithful cascade resolver for our filter rules ────────────────
#
# Every filter declaration nightpanel emits is user-origin !important, so among
# them the cascade winner is purely (specificity, source order). Our filter
# selectors are simple: a bare type (`video`, `canvas`, `img`, ...) or a type
# plus one substring-attribute test (`iframe[src*="/embed/"]`). We resolve only
# those — rules without a `filter` declaration (color/background/etc.) are
# irrelevant to which element gets dimmed and are ignored.

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
_ATTR_RE = re.compile(r"^([a-z0-9]+)\[([a-z-]+)\*=\"([^\"]+)\"\]$", re.IGNORECASE)


class _Element:
    def __init__(self, tag: str, *, src: str | None = None, cls: str = ""):
        self.tag = tag.lower()
        self.attrs = {"src": src} if src is not None else {}
        self.classes = set(cls.split())


def _parse_simple_selector(sel: str):
    """Return (tag, [(attr, substring), ...]) or None if too complex to model.

    We deliberately return None for anything beyond `tag` / `tag[attr*="v"]`
    so a future complex filter selector surfaces as an explicit modelling gap
    rather than a silently-wrong match.
    """
    sel = sel.strip()
    m = _ATTR_RE.match(sel)
    if m:
        return (m.group(1).lower(), [(m.group(2).lower(), m.group(3))])
    if re.fullmatch(r"[a-z0-9]+", sel, re.IGNORECASE):
        return (sel.lower(), [])
    return None


def _specificity(attr_conds) -> tuple[int, int, int]:
    # (ids, classes+attrs, types) — type selector contributes 1 type; each
    # attribute test contributes 1 to the middle field.
    return (0, len(attr_conds), 1)


def _matches(el: _Element, tag: str, attr_conds) -> bool:
    if el.tag != tag:
        return False
    for attr, substring in attr_conds:
        val = el.attrs.get(attr)
        if val is None or substring not in val:
            return False
    return True


def _filter_rules(css: str):
    """Yield (selector_str, filter_value, source_index) for each comma-split
    selector belonging to a rule that declares `filter`, in document order."""
    body = _COMMENT_RE.sub("", css)
    idx = 0
    for block in _BLOCK_RE.finditer(body):
        selectors, decls = block.group(1), block.group(2)
        fm = re.search(r"filter\s*:\s*([^;]+?)\s*!important", decls)
        if not fm:
            continue
        filter_value = fm.group(1).strip()
        for sel in selectors.split(","):
            sel = sel.strip()
            if sel:
                yield (sel, filter_value, idx)
                idx += 1


def _brightness_of(filter_value: str) -> float:
    """Extract the numeric brightness(...) argument from a filter string."""
    m = re.search(r"brightness\(([\d.]+)\)", filter_value)
    assert m, f"no brightness() in {filter_value!r}"
    return float(m.group(1))


def winning_filter(css: str, el: _Element):
    """The `filter` value that wins the cascade for `el`, or None if no filter
    rule matches (i.e. the element is left with its native/unfiltered value)."""
    best = None  # (specificity, source_index, value)
    for sel, value, order in _filter_rules(css):
        parsed = _parse_simple_selector(sel)
        if parsed is None:
            continue
        tag, attr_conds = parsed
        if _matches(el, tag, attr_conds):
            key = (_specificity(attr_conds), order)
            if best is None or key > best[0]:
                best = (key, value)
    return None if best is None else best[1]


# ── tier rendering tests ─────────────────────────────────────────────────────

# Sweep includes the adapter's clamp bounds (0.3 .. 1.5) and the default 0.9.
_BRIGHTNESS_SWEEP = [0.3, 0.45, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5]


def test_background_js_is_syntactically_valid():
    """`node --check` guards the JS template literal — would have caught the
    backtick-in-CSS-comment bug that silently breaks the whole script."""
    proc = subprocess.run(
        ["node", "--check", str(_BG_JS)], capture_output=True, text=True, timeout=20
    )
    assert proc.returncode == 0, proc.stderr


def test_renders_nonempty_css_with_nonce():
    css = render_css(0.9)
    assert css.strip()
    assert "npnonce" in css  # per-call nonce defeats Firefox insertCSS dedup


@pytest.mark.parametrize("b", _BRIGHTNESS_SWEEP)
def test_image_tier_is_half_brightness(b):
    css = render_css(b)
    win = winning_filter(css, _Element("img"))
    assert win is not None and "saturate(0.2)" in win and "sepia(0.4)" in win
    # Numeric tolerance, not a string match: JS toFixed rounds half away from
    # zero while Python rounds half to even, so the rendered "0.63" vs an
    # oracle "0.62" must not fail a *correct* value.
    assert abs(_brightness_of(win) - b * 0.5) <= 0.01, win


@pytest.mark.parametrize("b", _BRIGHTNESS_SWEEP)
def test_canvas_tier_is_fixed_moderate_dim_no_tint(b):
    """Functional canvas (Google Sheets grid) gets a plain, fixed ~80% dim
    regardless of the slider, and NO desaturate/sepia/hue tint."""
    css = render_css(b)
    win = winning_filter(css, _Element("canvas"))
    assert win == "brightness(0.80)", win
    for tint in ("saturate", "sepia", "hue-rotate"):
        assert tint not in win


@pytest.mark.parametrize("b", _BRIGHTNESS_SWEEP)
def test_image_dim_scales_with_brightness_but_canvas_does_not(b):
    css = render_css(b)
    img = winning_filter(css, _Element("img"))
    canvas = winning_filter(css, _Element("canvas"))
    assert abs(_brightness_of(img) - b * 0.5) <= 0.01
    assert canvas == "brightness(0.80)"


# ── cascade-outcome tests (the real point) ───────────────────────────────────


def test_video_is_never_dimmed():
    css = render_css(0.9)
    assert winning_filter(css, _Element("video")) == "none"
    # Even with a class a site might add to its player <video>.
    assert winning_filter(css, _Element("video", cls="html5-main-video")) == "none"


def test_video_excluded_from_background_transparent_rule():
    """The bg-flattening rule must keep :not(video) so the player surface
    isn't painted over."""
    css = render_css(0.9)
    body_rule = next(line for line in css.splitlines() if line.startswith("body, body *:not("))
    assert ":not(video)" in body_rule


@pytest.mark.parametrize(
    "src",
    [
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube-nocookie.com/embed/abc123",
        "https://player.vimeo.com/video/76979871",
    ],
)
def test_video_embed_iframes_are_crisp(src):
    """Embedded video players (a) must win `filter: none` over the broad iframe
    dim. This is the cascade assertion: the exclusion selector both
    out-specifies AND follows the bare `iframe` rule, so it wins."""
    css = render_css(0.9)
    assert winning_filter(css, _Element("iframe", src=src)) == "none"


@pytest.mark.parametrize(
    "src",
    [
        "https://ads.example.com/banner.html",
        "https://widget.disqus.com/comments",
        "https://maps.google.com/maps?q=x",
        # Discriminating cases: these contain the generic "/embed/" path but are
        # NOT video. The exclusion is scoped to known video hosts, so they must
        # stay dimmed — a regression to `iframe[src*="/embed/"]` would exempt
        # them (bright rectangles) and fail here.
        "https://disqus.com/embed/comments/?base=x",
        "https://platform.twitter.com/embed/Tweet.html?id=1",
        "https://www.google.com/maps/embed?pb=!1m18",
    ],
)
def test_non_video_iframes_remain_dimmed(src):
    """Regression guard: we did NOT blanket-disable iframe dimming. A non-video
    iframe must still get the heavy filter (no bright rectangles where
    allFrames injection fails)."""
    css = render_css(0.9)
    win = winning_filter(css, _Element("iframe", src=src))
    assert win is not None and "saturate(0.2)" in win and "brightness(0.45)" in win


@pytest.mark.parametrize("tag", ["img", "picture", "embed", "object"])
def test_decorative_media_stays_heavily_dimmed(tag):
    css = render_css(0.9)
    win = winning_filter(css, _Element(tag))
    assert win is not None and "saturate(0.2)" in win and "brightness(0.45)" in win


def test_embed_exclusion_follows_general_iframe_rule_in_source_order():
    """Source order matters for equal-or-lower specificity ties. Assert the
    exclusion physically comes after the bare-iframe rule, independent of the
    resolver, so a refactor that reorders them is caught."""
    css = _COMMENT_RE.sub("", render_css(0.9))
    bare = re.search(r"(^|\})\s*iframe\s*\{", css)
    excl = css.index('iframe[src*="youtube.com/embed"]')
    assert bare is not None and bare.start() < excl


# ── determinism / nonce hygiene ──────────────────────────────────────────────


def _strip_nonce(css: str) -> str:
    return re.sub(r"/\*npnonce[^*]*\*/", "", css, count=1).strip()


def test_renders_are_identical_modulo_nonce():
    """makeCss is brightness-deterministic except for the dedup nonce. The
    nonce must live ONLY in the leading comment — never leak into a rule."""
    a, b = render_css(0.9), render_css(0.9)
    assert a != b  # nonces differ
    assert _strip_nonce(a) == _strip_nonce(b)


def test_nonce_does_not_appear_inside_any_rule_body():
    css = render_css(0.9)
    for block in _BLOCK_RE.finditer(_COMMENT_RE.sub("", css)):
        assert "npnonce" not in block.group(2)


def test_stress_brightness_range_invariants():
    """Hammer the full clamp range (0.30 .. 1.50 in 0.01 steps, 121 renders in
    one node spawn): img dim is always exactly half-brightness and monotonic
    non-decreasing; canvas is always the fixed moderate dim; video always none;
    and every render is syntactically a CSS string with our nonce."""
    values = [round(0.30 + i * 0.01, 2) for i in range(121)]
    sheets = render_many(values)
    prev_img = -1.0
    for b, css in zip(values, sheets, strict=True):
        assert "npnonce" in css
        img = winning_filter(css, _Element("img"))
        cur = _brightness_of(img)
        assert abs(cur - b * 0.5) <= 0.01, f"b={b} img={img}"
        assert cur >= prev_img, f"non-monotonic at b={b}: {cur} < {prev_img}"
        prev_img = cur
        assert winning_filter(css, _Element("canvas")) == "brightness(0.80)"
        assert winning_filter(css, _Element("video")) == "none"
        # No element is left ambiguously matched by two equal-priority rules.
        for sel in ("iframe", "picture", "embed", "object"):
            assert winning_filter(css, _Element(sel)) is not None
