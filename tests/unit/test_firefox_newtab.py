# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for the Firefox bridge's NEW-TAB / NAVIGATION CSS path.

The reported bugs "css flaky on ff - resetting on new tabs" and "new tabs and
websites not respecting np scheme" both live in the ``tabs.onUpdated`` listener
in ``background.js`` — the code that re-injects the user-origin stylesheet every
time a tab loads a document. That listener is what the serialization /
re-inject-on-'loading' fixes (commits 2c49124, 49287ee) actually changed, yet
every other harness in this suite STUBS ``onUpdated`` out (``addListener() {}``),
so the navigation path shipped with zero automated coverage.

These tests capture the REAL ``onUpdated`` callback that background.js
registers, then fire synthetic browser events that faithfully model a document
lifecycle:

  * a fresh ``about:newtab`` is NOT injectable (skipped), then the tab
    navigates to a real URL ('loading' → 'complete');
  * **document teardown on 'loading'**: the previous document's user-origin
    sheet dies WITH the document, so the fake browser clears that tab's attached
    sheets at each 'loading' edge — exactly the condition that makes the
    listener's ``appliedCss.delete(tabId)`` necessary. Without that delete, the
    re-inject would try to ``removeCSS`` a sheet that no longer exists and (in
    the pre-nonce era) strand the page unstyled.

Assertions:
  1. a newly-navigated tab ends up with exactly ONE attached sheet (new tabs
     DO get the scheme);
  2. after an in-page navigation the tab still has exactly ONE sheet, never
     zero (the "resets / goes unstyled on navigation" symptom);
  3. no ``removeCSS`` ever targets a sheet that isn't attached (no stranding
     across the document teardown);
  4. the sheet count never exceeds one (no stacking across navigations).
"""

from __future__ import annotations

import json
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

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="node required to evaluate background.js"
)

# Node harness: load background.js (CommonJS test hook), capture the onUpdated
# callback it registers, and model attached sheets per tab WITH document
# teardown on every 'loading' edge. Drives a new-tab open + two navigations and
# prints a JSON result for the assertions below.
_NODE = r"""
const fs = require('fs');
const path = process.argv[process.argv.length - 1];
const src = fs.readFileSync(path, 'utf8').replace('connect();', '/* boot disabled */');

const sheets = new Map();                  // tabId -> Set(code) attached in the LIVE document
const calls = { insert: 0, remove: 0, removeFail: 0 };
const delay = (ms) => new Promise((r) => setTimeout(r, ms));
let onUpdatedCb = null;
let maxSheets = 0;
const note = (t) => { maxSheets = Math.max(maxSheets, sheets.get(t) ? sheets.get(t).size : 0); };

const browser = {
  tabs: {
    async executeScript() { await delay(1); return [1]; },
    async insertCSS(tabId, { code }) {
      await delay(5);
      if (!sheets.has(tabId)) sheets.set(tabId, new Set());
      sheets.get(tabId).add(code);
      calls.insert++;
      note(tabId);
    },
    async removeCSS(tabId, { code }) {
      await delay(3);
      calls.remove++;
      const s = sheets.get(tabId);
      if (!s || !s.has(code)) { calls.removeFail++; throw new Error('No such sheet to remove'); }
      s.delete(code);
    },
    async query() { return []; },          // start with no pre-existing tabs
    onUpdated: { addListener(fn) { onUpdatedCb = fn; } },
    onRemoved: { addListener() {} },
  },
  runtime: {
    onInstalled: { addListener() {} },
    connectNative() { return { onMessage: { addListener() {} }, onDisconnect: { addListener() {} } }; },
  },
  contentScripts: { async register() { return { async unregister() {} }; } },
  notifications: { create() {} },
};
const cons = { warn() {}, log() {}, error() {} };
const module = { exports: {} };
new Function('browser', 'console', 'module', 'Date', 'Math', src)(browser, cons, module, Date, Math);
const api = module.exports;

const size = (t) => (sheets.get(t) ? sheets.get(t).size : 0);
async function drainTab(t) {
  let last = null;
  for (let i = 0; i < 200; i++) {
    const tail = api.tabQueues.get(t);
    if (!tail || tail === last) break;
    last = tail;
    try { await tail; } catch (_) {}
  }
}

// A navigation: the previous document unloads (its user-origin sheet dies with
// it -> clear the live set) THEN the new document begins loading.
function fireLoading(tabId, url) {
  sheets.delete(tabId);                     // document teardown — old sheet gone
  onUpdatedCb(tabId, { status: 'loading' }, { id: tabId, url });
}
function fireComplete(tabId, url) {
  onUpdatedCb(tabId, { status: 'complete' }, { id: tabId, url });
}

(async () => {
  const out = {};
  await api.activate();                     // active = true; no tabs to style yet
  await drainTab(99);

  const TAB = 7;
  // 1. New tab opens on about:newtab (not injectable), then navigates to a URL.
  onUpdatedCb(TAB, { status: 'loading' }, { id: TAB, url: 'about:newtab' });  // skipped
  fireLoading(TAB, 'https://first.example/');
  fireComplete(TAB, 'https://first.example/');
  await drainTab(TAB);
  out.newtab_sheets = size(TAB);            // expect 1: the new tab got styled

  // 2. The same tab navigates to a different site (the "new website" case).
  fireLoading(TAB, 'https://second.example/page');
  fireComplete(TAB, 'https://second.example/page');
  await drainTab(TAB);
  out.after_nav_sheets = size(TAB);         // expect 1: NOT reset to unstyled

  // 3. One more navigation to hammer the teardown/re-inject cycle.
  fireLoading(TAB, 'https://third.example/');
  fireComplete(TAB, 'https://third.example/');
  await drainTab(TAB);
  out.after_nav2_sheets = size(TAB);        // expect 1

  out.max_sheets = maxSheets;               // must never exceed 1 (no stacking)
  out.removeFail = calls.removeFail;        // must be 0 (no stranded removes)
  process.stdout.write(JSON.stringify(out));
})();
"""


@pytest.fixture(scope="module")
def result() -> dict:
    proc = subprocess.run(
        ["node", "-e", _NODE, "--", str(_BG_JS)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"node harness failed:\n{proc.stderr}"
    return json.loads(proc.stdout)


def test_new_tab_gets_styled(result):
    # A freshly-navigated tab must end up with exactly one user-origin sheet —
    # new tabs/websites DO respect the NP scheme.
    assert result["newtab_sheets"] == 1, result


def test_navigation_does_not_leave_tab_unstyled(result):
    # The reported "resetting on new tabs" symptom: after navigating to a new
    # site the page must still carry exactly one sheet, never zero.
    assert result["after_nav_sheets"] == 1, result
    assert result["after_nav2_sheets"] == 1, result


def test_no_sheet_stacking_across_navigations(result):
    # The insert-new-then-peel-previous dance must never let two sheets coexist
    # at a stable point across the navigation sequence.
    assert result["max_sheets"] == 1, result


def test_no_stranded_removes_across_document_teardown(result):
    # appliedCss.delete(tabId) on 'loading' must keep the re-inject from trying
    # to removeCSS a sheet the destroyed document already took with it.
    assert result["removeFail"] == 0, result
