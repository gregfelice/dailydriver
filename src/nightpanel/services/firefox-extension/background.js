'use strict';

// nightpanel bridge — background script
//
// Two responsibilities while NP is active:
//   1. Inject user-origin CSS into every page (the SAAB instrument-cluster
//      theme — green-on-black, amber links, dimmed imagery).
//   2. Inject `<meta name="darkreader-lock">` into every page so the
//      Dark Reader extension (if installed) tears down its own theme via
//      its documented coexistence API. Without this, Dark Reader and
//      nightpanel race on document_start and Dark Reader's <style>
//      element (author-origin) often wins the visible paint even though
//      our user-origin !important would win the cascade once both are in
//      the DOM. See:
//        https://github.com/darkreader/darkreader/blob/main/CONTRIBUTING.md
//        src/inject/dynamic-theme/index.ts in darkreader/darkreader
//
// New-page coverage uses browser.contentScripts.register() so the meta
// is appended at document_start before Dark Reader's MutationObserver
// has even attached. For tabs that already exist at activate-time we
// run an executeScript pass to insert the meta retroactively.

const HOST = 'nightpanel';

// ── CSS ────────────────────────────────────────────────────────────────────
// Saab instrument cluster — direct CSS color overrides as USER-ORIGIN CSS.
//
// Why user-origin via tabs.insertCSS instead of a content-script <style>:
// Pages that use inline `style="color: ... !important"` (Wikipedia and many
// other sites do) beat any author-origin !important rule we inject. Only
// user-origin CSS overrides inline !important.
//
// Palette values are hardcoded here; they MUST stay in sync with
// nightpanel.palette.NIGHTPANEL until we render this file from the palette
// at build time.

function makeCss(brightness, videoBrightness) {
    // Images get aggressively dimmed — half the base brightness — so photos
    // and brand graphics don't pull the eye away from the muted text.
    const imgBrightness = (brightness * 0.5).toFixed(2);
    // <video> brightness is a SEPARATE, opt-in control (the "video brightness"
    // slider). Default 1.0 → emit `none`, not `brightness(1.0)`: a filter on
    // <video> can disable Firefox's GPU video-overlay path (forces compositing,
    // can break fullscreen/PiP), so the default must be a TRUE no-op that keeps
    // the picture crisp — preserving the long-standing "video stays untouched"
    // behavior. Only a user who drags the slider below 1.0 pays the filter cost.
    // Applied to the <video> element ONLY (not the youtube/vimeo embed iframes):
    // makeCss is injected allFrames, so an embedded player's inner youtube.com
    // frame dims its own <video>; dimming the outer iframe too would compose
    // multiplicatively (N²). A top-level youtube.com/watch page is a direct
    // <video>, so the primary case is a single, reliable application.
    const vb = typeof videoBrightness === 'number' ? videoBrightness : 1.0;
    const videoFilter = vb >= 1.0 ? 'none' : `brightness(${vb.toFixed(2)})`;
    // Functional <canvas> surfaces (spreadsheet grids, maps, drawing apps) are
    // content the user reads, not decoration. The artistic desaturate+sepia+
    // hue-rotate that flatters photos turns a data grid into an unreadable
    // green smear, so canvas gets only a plain, moderate dim. Fixed (not
    // brightness*factor) so a white grid lands at a legible ~80% regardless of
    // the slider — the user asked for "slightly reduced, still legible".
    const surfaceBrightness = '0.80';
    // PER-CALL NONCE in a CSS comment. Without this, makeCss is
    // brightness-deterministic — same brightness → byte-identical CSS.
    // Empirically (FF 140 ESR): when the same code is inserted twice into
    // the same tab (e.g. cross-origin navigation where 'loading' and
    // 'complete' both fire injectTab, or sequential nav A→B), Firefox
    // appears to dedupe the second insertCSS call. A later removeCSS
    // call with matching code then removes the *only* attached sheet,
    // leaving the page unstyled. The nonce makes every call's payload
    // unique so dedupe can't conflate inserts; removeCSS still works
    // because we track the exact code per tab in appliedCss.
    const nonce = `/*npnonce ${Date.now()}.${Math.random().toString(36).slice(2)}*/`;
    return `${nonce}
/* Solid NP black canvas */
html {
    background-color: #0A0A0A !important;
    color-scheme: dark !important;
}

/* Repaint every non-media background to the NP canvas black. We use a SOLID
 * color (not transparent): transparent let floating overlays — dropdowns,
 * menus, autocomplete popups, sticky/fixed headers — show the page content
 * behind them, which read as "broken/see-through" overlays. Painting them the
 * same solid #0A0A0A keeps the uniform-black canvas AND makes overlays opaque,
 * so stacked content no longer bleeds through. */
body, body *:not(img):not(video):not(svg):not(picture):not(canvas):not(iframe):not(embed):not(object) {
    background-color: #0A0A0A !important;
    background-image: none !important;
}

/* Default text color + borders: instrument-scale green on everything, icon
 * glyphs included (a green icon is on-theme). Font is handled separately below
 * so we can spare icon fonts. */
body, body * {
    color: #7DB890 !important;
    border-color: #2A2A2A !important;
}

/* Text font: Inter Light (matches the player) — but NOT on icon-font elements.
 * Icon fonts (Font Awesome, Material Icons/Symbols, Glyphicons, Bootstrap
 * Icons) map glyphs to private-use codepoints or ligatures; forcing Inter onto
 * them replaces the icon with tofu (□) or its raw ligature text ("home"). That
 * is the "broken fonts" symptom. By simply NOT matching these elements, their
 * own icon-font declaration wins the cascade and the glyph survives. Multi-line
 * selector on purpose: keeps the single-line "body, body star :not(...)" prefix
 * unique to the background rule above. */
body,
body *:not([class*="icon"]):not([class*="Icon"]):not([class*="fa-"]):not(.fa):not(.fas):not(.far):not(.fal):not(.fab):not(.fad):not([class*="material-symbols"]):not([class*="glyphicon"]):not([class*="bi-"]):not(.bi) {
    font-family: 'Inter', sans-serif !important;
    font-weight: 300 !important;
}

/* Code blocks / monospace: JetBrains Mono Light (matches the terminal) */
body pre, body code, body kbd, body samp, body tt, body var,
body pre *, body code *, body kbd *, body samp *, body tt *, body var * {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 300 !important;
}

/* Form inputs: leave font alone (user input ergonomics) but keep colors */
body input, body textarea, body select, body button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 300 !important;
}

/* Links: amber. Higher specificity wins over the text rule. */
body a, body a *, body a:link, body a:visited, body a:link * {
    color: #B08030 !important;
}

/* Link hover / focus: warm amber */
body a:hover, body a:hover *, body a:focus, body a:focus * {
    color: #E8930A !important;
}

/* Headings get the brighter green */
body h1, body h2, body h3, body h4, body h5, body h6,
body h1 *, body h2 *, body h3 *, body h4 *, body h5 *, body h6 * {
    color: #26DE81 !important;
}

/* Decorative imagery: heavy desaturation + slight green tint so photos and
 * brand graphics harmonize and don't pull the eye away from the muted text.
 * <video> is excluded everywhere — it's active content the user is watching
 * (YouTube, etc.); dimming it to half-brightness defeats the point. */
img, picture, embed, object {
    filter: saturate(0.2) sepia(0.4) hue-rotate(60deg) brightness(${imgBrightness}) !important;
}

/* Functional <canvas> surfaces (Google Sheets grid, maps, drawing apps): a
 * plain moderate dim, no tint. The grid is drawn on the canvas, so the
 * green/transparent text rules can't touch it — this filter is the only lever
 * on its brightness. Heavy desaturation here makes cell values unreadable. */
canvas {
    filter: brightness(${surfaceBrightness}) !important;
}

/* General iframes are dimmed as embedded imagery. We KEEP this (rather than
 * relying solely on allFrames injection theming the inner doc) because frame
 * injection is unreliable on FF ESR — see the insertCSS sync-barrier note in
 * injectTab — and an un-dimmed frame would flash as a bright rectangle. */
iframe {
    filter: saturate(0.2) sepia(0.4) hue-rotate(60deg) brightness(${imgBrightness}) !important;
}

/* …but video-player embeds are the content the user is watching. Leave the
 * picture crisp: the inner document is themed via allFrames injection (its own
 * <video> stays excluded), so the player chrome is dark while the video itself
 * is untouched. Scoped to KNOWN video hosts on purpose — a generic /embed/
 * match would also exempt Maps/Disqus/Twitter widgets and reintroduce the
 * bright-rectangle problem the bare iframe rule exists to prevent. Attribute
 * selectors out-specify and follow the bare iframe rule, so they win. */
iframe[src*="youtube.com/embed"],
iframe[src*="youtube-nocookie.com/embed"],
iframe[src*="player.vimeo.com"] {
    filter: none !important;
}

/* <video> brightness is driven by the dedicated "video brightness" slider via
 * videoFilter (see makeCss top). At the 1.0 default this is the keyword none — a
 * true no-op that keeps the GPU overlay path and leaves the picture crisp, the
 * long-standing default. Below 1.0 it dims the player (YouTube watch pages are
 * a top-level video element; embedded players dim via their inner frame rule). */
video {
    filter: ${videoFilter} !important;
}

/* Selection: NP dark green bg, bright green text */
::selection {
    background-color: #1A3020 !important;
    color: #26DE81 !important;
}
`;
}

// Meta-tag injection snippet. Runs in the page's content-script world,
// at document_start when registered as a contentScripts entry, or at
// runAt:'document_start' when fired via executeScript on existing tabs.
//
// Dedupe via querySelector — onUpdated fires both 'loading' and
// 'complete', and registered content scripts can co-fire alongside our
// executeScript pass on slow loads. (document.head || documentElement)
// because head can still be null at the earliest document_start tick.
const META_INJECT_JS = `
(function () {
    var target = document.head || document.documentElement;
    if (!target) return;
    if (document.querySelector('meta[name="darkreader-lock"]')) return;
    var m = document.createElement('meta');
    m.name = 'darkreader-lock';
    target.appendChild(m);
})();
`;

const META_REMOVE_JS = `
(function () {
    var m = document.querySelector('meta[name="darkreader-lock"]');
    if (m && m.parentNode) m.parentNode.removeChild(m);
})();
`;

// ── State ──────────────────────────────────────────────────────────────────

let active          = false;
let brightness      = 0.9;
// <video> brightness, driven by the dedicated slider. 1.0 = untouched (default).
// Held as a persistent global so a brightness-only command (or vice-versa)
// doesn't clobber the other value — each apply command carries only the
// field(s) that changed; we keep the last-applied value for the rest.
let videoBrightness = 1.0;
let port            = null;
// Track currently-attached user-origin sheet codes per tab so we can
// removeCSS() with the exact code. A LIST, not a single value: revert peels
// off *every* sheet, so even if a prior race ever stacked more than one, the
// page still clears completely on toggle-off (the belt to the per-tab queue's
// suspenders).
const appliedCss = new Map();   // tabId -> string[]
// Per-tab promise chain. Every insertCSS/removeCSS for a tab runs through this
// so the calls never overlap. Overlapping injects were the root cause of the
// CSS-switch bugs: two in-flight injectTab calls would both read the same
// `previous`, both insert, and only one removeCSS would match — stranding the
// other sheet (stacked dimming on drag; CSS that won't clear on toggle-off).
const tabQueues  = new Map();   // tabId -> Promise (chain tail)
// Drag coalescing. A slider drag fires many brightness updates; we keep only
// the LATEST target per tab and collapse the burst into at most one in-flight
// + one queued injection instead of running every intermediate value.
const pendingB     = new Map(); // tabId -> latest brightness awaiting injection
const injectQueued = new Set(); // tabIds that already have an injection queued
// Handle to the registered content script that injects the darkreader-lock
// meta tag at document_start on every page. Held while active === true.
let darkReaderLockScript = null;
// Global chain for state TOGGLES (activate/deactivate) so rapid ON/OFF clicks
// resolve in receipt order regardless of each pass's internal awaits. Plain
// brightness updates while active bypass this (per-tab coalesced reinject) so a
// slider drag isn't serialized behind a full all-tabs pass per tick.
let toggleChain = Promise.resolve();

// Run an async op for a tab strictly after the tab's previous op finishes.
function enqueue(tabId, fn) {
    const tail = tabQueues.get(tabId) || Promise.resolve();
    const run = tail.then(fn, fn);          // run regardless of prior outcome
    tabQueues.set(tabId, run.catch(() => {}));
    return run;
}

// Expected, non-actionable failures: discarded/privileged/gone/not-yet-scriptable
// tabs. tabs.insertCSS/removeCSS/executeScript reject on these (Mozilla bugs
// 1611878 / 1450371 and friends); the onUpdated listener re-covers them on their
// next real load. Swallow these quietly; log everything else.
function isBenign(e) {
    const m = (e && e.message) || String(e || '');
    return /no window matching|discarded|missing host permission|cannot? .*access|no tab(?: with id)?|invalid tab|frame not found|cannot be scripted|moz-extension:|about:|chrome:|resource:/i.test(m);
}
function warnReal(label, tabId, e) {
    if (!isBenign(e)) console.warn(`nightpanel: ${label} for tab`, tabId, e);
}

// ── Install notice ─────────────────────────────────────────────────────────

browser.runtime.onInstalled.addListener(({ reason }) => {
    if (reason !== 'install') return;
    browser.notifications.create('np-installed', {
        type:    'basic',
        title:   'nightpanel bridge installed',
        message: 'Toggle nightpanel from the nightpanel app or the GNOME panel button.',
    });
});

// ── Native host connection ─────────────────────────────────────────────────

function connect() {
    try {
        port = browser.runtime.connectNative(HOST);
        port.onMessage.addListener(onCommand);
        port.onDisconnect.addListener(() => {
            port = null;
            setTimeout(connect, 5000);
        });
    } catch (e) {
        setTimeout(connect, 15000);
    }
}

function onCommand(cmd) {
    if (!cmd || typeof cmd.action !== 'string') return;
    if (cmd.action === 'apply') {
        // Keep-last per field: a command may carry brightness, videoBrightness,
        // or both (slider drags send only the one that moved; the Firefox
        // adapter's initial apply sends both). Update only what's present so a
        // videoBrightness-only command can't reset brightness, and vice-versa.
        if (typeof cmd.brightness === 'number')      brightness      = cmd.brightness;
        if (typeof cmd.videoBrightness === 'number') videoBrightness = cmd.videoBrightness;
        if (!active) {
            // Toggle ON — serialize against other toggles so a racing OFF can't
            // land out of order.
            toggleChain = toggleChain.then(activate).catch(() => {});
        } else {
            // Brightness/video update while already on — lightweight per-tab,
            // coalesced reinject. No full activate() (no meta re-register, no
            // toggle-chain wait), so drags stay responsive.
            reinjectAllTabs();
        }
    } else if (cmd.action === 'revert') {
        toggleChain = toggleChain.then(deactivate).catch(() => {});
    }
}

// ── CSS apply / remove (user-origin via tabs.insertCSS) ────────────────────

// Internal: do one injection. Always runs inside the per-tab queue (via
// injectTab), so it never overlaps another op on the same tab — which is what
// makes the read-of-`previous` / set-of-appliedCss / remove-of-previous
// sequence atomic and keeps sheets from stacking.
async function doInjectTab(tabId, b) {
    const css = makeCss(b, videoBrightness);
    const previous = appliedCss.get(tabId) || [];
    // Synchronization barrier: a no-op executeScript round-trip before
    // insertCSS. Empirically (Firefox ESR 140) tabs.insertCSS called from
    // the onUpdated 'loading' branch can silently fail to apply — the call
    // resolves but the user-origin stylesheet never attaches. A prior
    // executeScript blocks until the tab's content-script world is
    // initialized, after which insertCSS lands reliably.
    try { await browser.tabs.executeScript(tabId, { code: '1' }); } catch (_) {}
    try {
        // Insert NEW CSS first, then peel off the previous block(s). During the
        // brief overlap both are active and the new one wins (last-declared,
        // same origin/specificity). Remove-then-insert would leave one unstyled
        // paint cycle — the flash users saw on slider drags.
        await browser.tabs.insertCSS(tabId, {
            code:      css,
            cssOrigin: 'user',          // beats inline !important from the page
            allFrames: true,
            runAt:     'document_start',
        });
    } catch (e) {
        // New sheet never attached — leave `previous` in place so the page
        // isn't stripped bare, and don't record a phantom sheet.
        warnReal('insertCSS failed', tabId, e);
        return;
    }
    appliedCss.set(tabId, [css]);
    for (const prev of previous) {
        try {
            await browser.tabs.removeCSS(tabId, { code: prev, cssOrigin: 'user', allFrames: true });
        } catch (e) {
            warnReal('removeCSS(prev) failed', tabId, e);
        }
    }
}

// Internal: remove every sheet currently attached to a tab. Runs inside the
// per-tab queue. Clearing the WHOLE list (not a single code) is what guarantees
// a page fully reverts on toggle-off even if it ever ended up multi-layered.
async function doRemoveTab(tabId) {
    const list = appliedCss.get(tabId);
    appliedCss.delete(tabId);
    if (!list || !list.length) return;
    for (const css of list) {
        try {
            await browser.tabs.removeCSS(tabId, { code: css, cssOrigin: 'user', allFrames: true });
        } catch (e) {
            warnReal('removeCSS failed', tabId, e);
        }
    }
}

// Public: queue a (coalesced) injection for a tab. A burst of calls collapses
// to at most one in-flight + one queued op; the queued op applies the LATEST
// requested brightness. Returns the tab's chain tail so callers/tests can await.
function injectTab(tabId, b) {
    pendingB.set(tabId, b);
    if (injectQueued.has(tabId)) return tabQueues.get(tabId) || Promise.resolve();
    injectQueued.add(tabId);
    return enqueue(tabId, async () => {
        injectQueued.delete(tabId);
        if (!pendingB.has(tabId)) return;       // cancelled by removeTab
        const latest = pendingB.get(tabId);
        pendingB.delete(tabId);
        await doInjectTab(tabId, latest);
    });
}

// Public: queue a full clear for a tab, cancelling any pending injection so we
// don't re-apply CSS we're about to remove.
function removeTab(tabId) {
    pendingB.delete(tabId);
    injectQueued.delete(tabId);
    return enqueue(tabId, () => doRemoveTab(tabId));
}

async function injectMeta(tabId) {
    try {
        await browser.tabs.executeScript(tabId, {
            code:      META_INJECT_JS,
            allFrames: false,
            runAt:     'document_start',
        });
    } catch (e) {
        console.warn('nightpanel: meta inject failed for tab', tabId, e);
    }
}

async function removeMeta(tabId) {
    try {
        await browser.tabs.executeScript(tabId, {
            code:      META_REMOVE_JS,
            allFrames: false,
            runAt:     'document_start',
        });
    } catch (e) {
        console.warn('nightpanel: meta remove failed for tab', tabId, e);
    }
}

async function registerMetaScript() {
    if (darkReaderLockScript) return;
    try {
        darkReaderLockScript = await browser.contentScripts.register({
            matches:   ['<all_urls>'],
            js:        [{ code: META_INJECT_JS }],
            runAt:     'document_start',
            allFrames: false,
        });
    } catch (e) {
        console.warn('nightpanel: contentScripts.register failed:', e);
        darkReaderLockScript = null;
    }
}

async function unregisterMetaScript() {
    if (!darkReaderLockScript) return;
    try {
        await darkReaderLockScript.unregister();
    } catch (e) {
        console.warn('nightpanel: contentScripts.unregister failed:', e);
    } finally {
        darkReaderLockScript = null;
    }
}

function isInjectable(url) {
    if (!url) return false;
    return !url.startsWith('about:') &&
           !url.startsWith('moz-extension:') &&
           !url.startsWith('chrome:') &&
           !url.startsWith('resource:');
}

async function applyToAllTabs() {
    const tabs = await browser.tabs.query({});
    for (const tab of tabs) {
        // Skip discarded tabs. tabs.insertCSS rejects on them (Mozilla bug
        // 1611878 / 1450371), and tabs.executeScript would too. Firefox
        // restores a discarded tab via a fresh load when the user focuses
        // it; tabs.onUpdated fires 'loading' then 'complete' and our
        // listener (plus the registered document_start content script for
        // the meta) handles the tab from there.
        if (tab.discarded) continue;
        if (!isInjectable(tab.url)) continue;
        injectTab(tab.id, brightness);
        injectMeta(tab.id);
    }
}

// Brightness/video changed while already active: re-apply the CSS (coalesced
// per tab) without re-registering the meta script or touching the toggle chain.
async function reinjectAllTabs() {
    const tabs = await browser.tabs.query({});
    for (const tab of tabs) {
        if (tab.discarded) continue;
        if (!isInjectable(tab.url)) continue;
        injectTab(tab.id, brightness);
    }
}

async function activate() {
    // brightness / videoBrightness are set by onCommand before this runs; we
    // render from the globals so a single-field command keeps the other value.
    active = true;
    // Register the meta-tag content script FIRST so new navigations that
    // race with our applyToAllTabs pass still get the early-injection path.
    await registerMetaScript();
    await applyToAllTabs();
}

async function deactivate() {
    active = false;
    await unregisterMetaScript();
    const tabs = await browser.tabs.query({});
    for (const tab of tabs) {
        if (tab.discarded) continue;
        if (!isInjectable(tab.url)) continue;
        removeTab(tab.id);
        removeMeta(tab.id);
    }
}

// Re-inject on new page loads while active.
// 'loading' is the critical event: the previous document has unloaded (taking
// our user-origin CSS with it) and the new one is about to render. insertCSS
// with runAt:'document_start' grabs the new document before the page's own
// stylesheets paint, eliminating the flash users see during navigation.
// 'complete' is a defensive re-inject in case a late-arriving stylesheet
// from the page knocked our rules out of effective stacking order.
//
// IMPORTANT: clear appliedCss[tabId] on 'loading'. The old document's
// user-origin stylesheet was destroyed with the document, but our map
// still remembers its code. If we left it, injectTab's insert-then-
// remove-previous pass would call removeCSS with the SAME code it just
// inserted (since makeCss is brightness-deterministic) — Firefox happily
// removes the freshly-attached sheet and the page ends up unstyled. This
// was the cause of the C4/C5 permutation failures: "page after first
// navigation looks unstyled". Slider-drag brightness changes inside one
// document are unaffected: those don't fire 'loading'.
//
// The meta tag is handled by the registered content script
// (browser.contentScripts.register) — it fires at document_start before
// this listener and is deduped by the querySelector guard inside the
// snippet, so we don't redundantly re-inject it here.
browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (!active || !isInjectable(tab.url)) return;
    if (changeInfo.status === 'loading') {
        appliedCss.delete(tabId);
    }
    if (changeInfo.status === 'loading' || changeInfo.status === 'complete') {
        injectTab(tabId, brightness);
    }
});

// Clean up all per-tab state when a tab closes (don't leak queue/coalesce
// entries for dead tabs).
browser.tabs.onRemoved.addListener((tabId) => {
    appliedCss.delete(tabId);
    tabQueues.delete(tabId);
    pendingB.delete(tabId);
    injectQueued.delete(tabId);
});

// ── Boot ──────────────────────────────────────────────────────────────────

connect();

// Test hook: inert in the browser (no CommonJS `module`), but lets the node
// harness in tests/unit/test_firefox_switch.py drive the switch machinery.
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        makeCss, onCommand, injectTab, removeTab, activate, deactivate,
        appliedCss, tabQueues,
    };
}
