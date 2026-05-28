# Test plan — 2026-05-27 session changes

Strategies named per `testing.md`. Each change below maps to the strategies that apply, the artifacts produced, and the empirical results.

## Surfaces under test

1. `tests/conftest.py` — autouse privilege-escalation guard
2. `src/nightpanel/adapters/gnome.py` — `_bounce_nautilus()` helper + apply/revert calls
3. `src/nightpanel/services/firefox-extension/{background.js,manifest.json}` — v2.6 page-content extension
4. `src/nightpanel/renderers/firefox_chrome.py` + `src/nightpanel/adapters/firefox.py::_install_user_chrome` — slimfox / userChrome.css UI styling

## Surface 1 — conftest privilege-escalation guard

**Strategy:** Component / Isolation Testing + regression of the original trigger.
**Artifacts:** `tests/unit/test_subprocess_guard.py` (11 tests).
**Empirical results:**
- 11/11 PASS in 0.02 s
- Regression test (`test_apply_modifier_config_success` — the one that was prompting for pkexec): now fails in 0.18 s with a clear RuntimeError; no system prompt
- 33 tests in `test_hid_apple` / `test_claude_code` / `test_gemini_cli` that mock subprocess in-test all still PASS

## Surface 2 — gnome adapter `_bounce_nautilus`

**Strategy:** Integration Testing against real `nautilus` + `gapplication`.
**Empirical results:**
- No-op when nautilus not running: `gapplication action ...` returns 0, helper returns cleanly — PASS
- Kill when running: launched `nautilus --no-default-window` (PID 1736723), called `_bounce_nautilus()` via the real import, nautilus exited within 1 s — PASS

## Surface 3 — Firefox extension v2.6 (page content)

### 3a. Component / Isolation
**Artifact:** `/tmp/np-ext-test.js` — `background.js` loaded under stubbed `browser.*` API in node.
**Result:** 14/14 assertions PASS — content script registered before insertCSS, discarded tabs skipped, about:URLs skipped, executeScript code contains darkreader-lock injection, cssOrigin='user' everywhere, revert unregisters + removes both CSS and meta.

### 3b. End-to-End permutation matrix
**Artifacts:** `/tmp/np-marionette-matrix-headed.py` (headed under Xvfb), `/tmp/np-ff-e2e/` (isolated profile + fake HOME + stub native host + http server).

**Browser scope:** Firefox-family only (`browser_specific_settings.gecko` in manifest). Empirically tested on Firefox ESR 140.11.0. Chromium 148 confirmed to silently reject the MV2 manifest (Chromium dropped MV2 ~v127 and lacks `cssOrigin: 'user'` + `browser.contentScripts.register`). Brave / Edge are Chromium-based; same exclusion. LibreWolf / Floorp / Tor / Waterfox not present on system; gecko-family, likely compatible but not empirically verified.

**Cells:**
| Cell | Scenario | Headed (Xvfb) |
|---|---|---|
| C1 | existing tab → marionette Navigate | PASS |
| C2 | new tab via WebDriver:NewWindow → Navigate | PASS |
| C3 | window.open new tab → URL | PASS |
| C4 | sequential same-tab Nav A → Nav B | PASS |
| C5 | location.href JS-driven nav | PASS |
| C6 | third sequential nav | PASS |
| C7 | WebDriver:NewWindow type=window → Navigate | PASS |
| C8 | new tab → about:newtab → Navigate (user-reported scenario) | PASS |

### 3c. Timing fuzz
**Artifact:** `/tmp/np-marionette-fuzz.py` — randomizes activation / post-nav / post-switch / post-window-open latencies per iteration.
**Result:** 8 iterations × 8 cells = **64/64 PASS** with random latencies spanning activation 3.97–11.78 s, post-nav 0.52–3.87 s, post-switch 0.19–1.94 s, post-window-open 0.15–1.89 s.

### 3d. Toggle abuse / state-machine stress
**Artifact:** `/tmp/np-marionette-abuse.py` + `/tmp/np-host-toggle.py` (control-file-driven native host stub).
**Result:** **6/6 patterns PASS** —
| Pattern | Result |
|---|---|
| P1: 4 slow toggles, end apply → NP ON | PASS |
| P2: 4 slow toggles, end revert → NP OFF | PASS |
| P3: 20 fast toggles 10 ms apart, end apply → NP ON | PASS |
| P4: 20 fast toggles 10 ms apart, end revert → NP OFF | PASS |
| P5: 10 mixed jittered (5–500 ms), end apply → NP ON | PASS |
| P6: 10 mixed jittered, end revert → NP OFF | PASS |

### Real bugs uncovered during testing (both now fixed)

**Bug 1: `tabs.insertCSS` race with content-script-world initialization.**
On the early `loading` phase of `onUpdated`, insertCSS resolves but the user-origin stylesheet doesn't attach. Fix: `await browser.tabs.executeScript(tabId, {code: '1'})` synchronization barrier at the top of `injectTab`. Empirically reproduced by toggling the fix on/off and seeing CSS application flip.

**Bug 2: `appliedCss[tabId]` stale across navigations.**
After C1 left appliedCss[tab]=css, C4's sequential navigation called injectTab → insertCSS(css) then immediately removeCSS(css, previous=css) — removing the freshly-attached sheet. Net: zero CSS. Fix: clear `appliedCss.delete(tabId)` on `changeInfo.status === 'loading'` so each navigation starts with no stale previous. Verified by C4/C5 flipping FAIL→PASS after fix.

Both bugs almost certainly affected v2.5 too — they explain the user-reported "any tab not focused when NP activated doesn't get scheme."

## Surface 4 — slimfox / userChrome.css

**Strategy:** Component (renderer determinism) + Adapter integration (file-write + pref).
**Artifact:** `tests/unit/test_firefox_chrome.py` (10 tests).
**Result:** 10/10 PASS in 0.03 s —
- Renderer deterministic per palette ✓
- Palette values thread through to rendered CSS ✓
- Slimfox `#navigator-toolbox` collapse rule present ✓
- All 6 nightpanel sharp-corner CSS vars present ✓
- `apply()` writes userChrome.css matching renderer ✓
- `apply()` sets `toolkit.legacyUserProfileCustomizations.stylesheets=true` in user.js ✓
- Pref idempotent (no duplication on re-apply) ✓
- Existing user.js prefs preserved ✓
- `apply()` writes np-command.json with "apply" + brightness ✓
- `revert()` writes "revert" command but DELIBERATELY leaves userChrome.css alone (Firefox can't hot-reload chrome.css) ✓

## Permutation matrix dimensions exercised

Per the testing-permutation memory:
- **Tab origin** — existing-before-activate (C1, C4, C5, C6), new-via-WebDriver-tab (C2), window.open (C3), new-via-WebDriver-window (C7), via about:newtab transition (C8) ✓
- **Starting URL** — about:blank (C1, C2), about:newtab (C8), http (C4–C6), file:// (informational from earlier) ✓
- **Navigation method** — WebDriver:Navigate (C1, C2, C4, C6, C7, C8), window.open (C3), location.href (C5) ✓
- **Focus state** — focused (all cells), background (not covered — no listener for focus changes, low risk)
- **Repeat behavior** — first nav (C1), second (C4), third (C6), many rapid toggles (P3, P4) ✓
- **Browser variant** — Firefox ESR 140 ✓; Chromium scope confirmed (incompatible by design) ✓; other Gecko forks not present
- **Render mode** — headless + Xvfb-headed ✓
- **Latency** — randomized across 8 iterations × 8 cells ✓
- **Toggle frequency** — slow (1 s) through 10 ms bursts ✓

## Coverage gaps explicitly acknowledged

- **Tab discard + restore** (Auto Tab Discard) — extension code skips discarded tabs in applyToAllTabs and relies on onUpdated `loading`+`complete` to inject on restore; not driven empirically in the matrix because Marionette doesn't expose `tabs.discard()` directly.
- **Background-tab focus events** — extension has no `onActivated` listener; not currently in scope.
- **iframe-heavy and cross-origin pages** — CSS injection uses `allFrames: true`; not explicitly tested.
- **Real Firefox Ctrl+T address-bar flow** — Marionette `WebDriver:NewWindow` doesn't traverse the FF urlbar UI; C8 is the closest proxy.
- **Other Gecko forks** (LibreWolf, Floorp, Tor, Waterfox) — likely compatible, not empirically tested.

## Artifacts left in the repo

- `tests/conftest.py` — guard fixture (committed)
- `tests/unit/test_subprocess_guard.py` — 11 tests
- `tests/unit/test_firefox_chrome.py` — 10 tests
- `np-test-plan.md` — this file

## Artifacts staged in /tmp (reproducible test harness, not in repo)

- `/tmp/np-marionette-matrix-headed.py` — 8-cell headed matrix
- `/tmp/np-marionette-fuzz.py` — timing fuzz
- `/tmp/np-marionette-abuse.py` — toggle abuse
- `/tmp/np-ext-test.js` — node component sim
- `/tmp/np-host-toggle.py` — control-file native-host stub
- `/tmp/np-ff-e2e/` — isolated test profile + fake HOME + stub host JSON
- `/tmp/nightpanel-bridge-v2.6.xpi` — built XPI (also deployed to user's profile)
