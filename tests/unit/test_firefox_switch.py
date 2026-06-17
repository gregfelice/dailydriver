# SPDX-License-Identifier: GPL-3.0-or-later
"""Concurrency tests for the Firefox bridge's CSS switch machinery.

``background.js`` injects/removes user-origin stylesheets per tab. Before the
hardening these calls weren't serialized, so overlapping injects (slider drags,
apply/revert overlap) raced on the per-tab ``appliedCss`` bookkeeping and
stacked or stranded sheets — the reported "switch" bugs: dimming that piles up
on a drag, and CSS that won't clear on toggle-off.

These tests evaluate the REAL background.js in node with a fake ``browser``
whose insertCSS/removeCSS model the set of sheets actually attached per tab
(with artificial async delay to force overlap), then drive the switch entry
points and assert:

  * a burst of injects collapses to ONE attached sheet (no stacking) and is
    coalesced (few inserts, not one per call);
  * sequential injects each peel off the previous sheet (steady-state = 1);
  * removeTab / deactivate fully clear the tab (revert leaves nothing);
  * no removeCSS ever targets a sheet that isn't attached (no stranding /
    double-remove).
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

# Node harness: load background.js as CommonJS (module.exports test hook), with a
# fake browser that tracks attached sheets per tab and adds latency so overlapping
# ops actually interleave. Prints a JSON result object for the assertions below.
_NODE = r"""
const fs = require('fs');
const path = process.argv[process.argv.length - 1];  // last arg = bg.js path
const src = fs.readFileSync(path, 'utf8').replace('connect();', '/* boot disabled */');

const sheets = new Map();                       // tabId -> Set(code)  (what's attached)
const calls = { insert: 0, remove: 0, removeFail: 0 };
const delay = (ms) => new Promise((r) => setTimeout(r, ms));
const TABS = [{ id: 1, url: 'https://a.example', discarded: false },
              { id: 2, url: 'https://b.example', discarded: false }];

const browser = {
  tabs: {
    async executeScript() { await delay(1); return [1]; },
    async insertCSS(tabId, { code }) {
      await delay(5);                            // slow insert => forces overlap
      if (!sheets.has(tabId)) sheets.set(tabId, new Set());
      sheets.get(tabId).add(code);
      calls.insert++;
    },
    async removeCSS(tabId, { code }) {
      await delay(3);
      calls.remove++;
      const s = sheets.get(tabId);
      if (!s || !s.has(code)) { calls.removeFail++; throw new Error('No such sheet to remove'); }
      s.delete(code);
    },
    async query() { return TABS; },
    onUpdated: { addListener() {} },
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
async function drainAll() { for (const t of [1, 2]) await drainTab(t); }

(async () => {
  const out = {};

  // 1. Coalesced burst: 20 overlapping injects on one tab.
  for (let i = 0; i < 20; i++) api.injectTab(1, 0.3 + i * 0.05);
  await drainTab(1);
  out.burst_sheets = size(1);
  out.burst_inserts = calls.insert;

  // 2. Sequential cycles: each must peel the previous sheet (no stacking).
  const insB = calls.insert, remB = calls.remove;
  for (let i = 0; i < 5; i++) { api.injectTab(1, 0.5 + i * 0.05); await drainTab(1); }
  out.seq_sheets = size(1);
  out.seq_inserts = calls.insert - insB;
  out.seq_removes = calls.remove - remB;

  // 3. removeTab fully clears the tab.
  api.removeTab(1);
  await drainTab(1);
  out.after_remove_sheets = size(1);

  // 4. activate() styles every tab; deactivate() clears every tab.
  await api.activate();   await drainAll();
  out.activate_sheets = size(1) + size(2);
  await api.deactivate(); await drainAll();
  out.deactivate_sheets = size(1) + size(2);

  out.removeFail = calls.removeFail;
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


def test_burst_does_not_stack_sheets(result):
    # A 20-update drag must leave exactly ONE attached sheet, not a pile.
    assert result["burst_sheets"] == 1


def test_burst_is_coalesced(result):
    # The 20 synchronous updates collapse to at most a couple of real inserts.
    assert result["burst_inserts"] <= 2, result


def test_sequential_injects_peel_previous(result):
    # Five separate injects: steady state is one sheet, each cycle removed the
    # prior one (so inserts and removes both ran five times).
    assert result["seq_sheets"] == 1
    assert result["seq_inserts"] == 5
    assert result["seq_removes"] == 5


def test_remove_tab_clears_completely(result):
    assert result["after_remove_sheets"] == 0


def test_activate_then_deactivate_round_trip(result):
    assert result["activate_sheets"] == 2, "both tabs should be styled after activate"
    assert result["deactivate_sheets"] == 0, "no sheet may survive deactivate"


def test_no_stranded_or_double_removes(result):
    # Every removeCSS targeted a sheet that was actually attached.
    assert result["removeFail"] == 0


# ── benign-vs-real error quieting (console spam) ─────────────────────────────

_NODE_WARN = r"""
const fs = require('fs');
const path = process.argv[process.argv.length - 1];
const src = fs.readFileSync(path, 'utf8').replace('connect();', '/* boot disabled */');
const delay = (ms) => new Promise((r) => setTimeout(r, ms));
let warns = 0;
const cons = { warn() { warns++; }, log() {}, error() {} };

// Tab 1: insertCSS fails with a BENIGN error (discarded/privileged tab) -> quiet.
// Tab 2: a sheet attaches, then removeCSS fails with a REAL error -> logged.
const attached = new Set();
const browser = {
  tabs: {
    async executeScript() { await delay(1); return [1]; },
    async insertCSS(tabId, { code }) {
      await delay(1);
      if (tabId === 1) throw new Error('No window matching {"matchesHost":[]}');  // benign
      attached.add(code);
    },
    async removeCSS(tabId) { await delay(1); throw new Error('boom: unexpected internal failure'); },  // real
    async query() { return []; },
    onUpdated: { addListener() {} },
    onRemoved: { addListener() {} },
  },
  runtime: { onInstalled: { addListener() {} }, connectNative() { return { onMessage: { addListener() {} }, onDisconnect: { addListener() {} } }; } },
  contentScripts: { async register() { return { async unregister() {} }; } },
  notifications: { create() {} },
};
const module = { exports: {} };
new Function('browser', 'console', 'module', 'Date', 'Math', src)(browser, cons, module, Date, Math);
const api = module.exports;
async function drain(t) { let last=null; for (let i=0;i<50;i++){ const x=api.tabQueues.get(t); if(!x||x===last) break; last=x; try{await x;}catch(_){} } }

(async () => {
  api.injectTab(1, 0.9); await drain(1);     // benign insert failure -> no warn
  const afterBenign = warns;
  api.injectTab(2, 0.9); await drain(2);     // attaches one sheet
  api.injectTab(2, 0.8); await drain(2);     // removeCSS(prev) fails for real -> warn
  process.stdout.write(JSON.stringify({ afterBenign, total: warns }));
})();
"""


def test_benign_errors_quiet_real_errors_logged():
    proc = subprocess.run(
        ["node", "-e", _NODE_WARN, "--", str(_BG_JS)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"node harness failed:\n{proc.stderr}"
    out = json.loads(proc.stdout)
    assert out["afterBenign"] == 0, "a benign insertCSS failure must not warn"
    assert out["total"] >= 1, "a real removeCSS failure must still be logged"
