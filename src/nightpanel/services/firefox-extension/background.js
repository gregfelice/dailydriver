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

function makeCss(brightness) {
    // Images get aggressively dimmed — half the base brightness — so photos
    // and brand graphics don't pull the eye away from the muted text.
    const imgBrightness = (brightness * 0.5).toFixed(2);
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

/* Kill every non-media background so html's black shows through uniformly */
body, body *:not(img):not(video):not(svg):not(picture):not(canvas):not(iframe):not(embed):not(object) {
    background-color: transparent !important;
    background-image: none !important;
}

/* Default text: instrument-scale green + Inter Light (matches the player) */
body, body * {
    color: #7DB890 !important;
    border-color: #2A2A2A !important;
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

/* Images: heavy desaturation + slight green tint so they harmonize.
 * <video> is excluded — videos are active content the user is watching
 * (YouTube, etc.); dimming them to half-brightness defeats the point. */
img, canvas, iframe, picture, embed, object {
    filter: saturate(0.2) sepia(0.4) hue-rotate(60deg) brightness(${imgBrightness}) !important;
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

let active     = false;
let brightness = 0.9;
let port       = null;
// Track the last-applied CSS per tab so we can removeCSS() with the same code.
const appliedCss = new Map();
// Handle to the registered content script that injects the darkreader-lock
// meta tag at document_start on every page. Held while active === true.
let darkReaderLockScript = null;

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
    if (cmd.action === 'apply')  activate(cmd.brightness ?? 0.9);
    if (cmd.action === 'revert') deactivate();
}

// ── CSS apply / remove (user-origin via tabs.insertCSS) ────────────────────

async function injectTab(tabId, b) {
    const css = makeCss(b);
    const previous = appliedCss.get(tabId);
    // Synchronization barrier: a no-op executeScript round-trip before
    // insertCSS. Empirically (Firefox ESR 140) tabs.insertCSS called from
    // the onUpdated 'loading' branch can silently fail to apply — the
    // call resolves but the user-origin stylesheet never attaches to the
    // document. A prior executeScript blocks until the tab's
    // content-script world is initialized, after which insertCSS lands
    // reliably. Without this barrier the E2E test (np-marionette-test2.py)
    // observes html bg = rgba(0,0,0,0) on a freshly-loaded page; with it,
    // html bg = rgb(10,10,10) as designed.
    try { await browser.tabs.executeScript(tabId, { code: '1' }); } catch (_) {}
    try {
        // Insert NEW CSS first, then remove the previous block. During the
        // brief overlap, both stylesheets are active; the new one wins on
        // same-origin same-specificity (last-declared rule). Order matters:
        // doing remove-then-insert with an await between them leaves one
        // paint cycle where the user-origin override is gone, which is the
        // visible flash users see during slider drags.
        await browser.tabs.insertCSS(tabId, {
            code:      css,
            cssOrigin: 'user',          // beats inline !important from the page
            allFrames: true,
            runAt:     'document_start',
        });
        appliedCss.set(tabId, css);
        if (previous) {
            try {
                await browser.tabs.removeCSS(tabId, {
                    code:      previous,
                    cssOrigin: 'user',
                    allFrames: true,
                });
            } catch (e) {
                console.warn('nightpanel: removeCSS failed for tab', tabId, e);
            }
        }
    } catch (e) {
        // tabs.insertCSS silently rejects on discarded tabs and on tabs
        // whose document hasn't created a window global yet (Mozilla bugs
        // 1611878 and 1450371). The onUpdated listener picks them up on
        // their next real load, so this is non-fatal — but we log it so
        // the next debug session doesn't have to rediscover the failure.
        console.warn('nightpanel: insertCSS failed for tab', tabId, e);
    }
}

async function removeTab(tabId) {
    const css = appliedCss.get(tabId);
    if (!css) return;
    try {
        await browser.tabs.removeCSS(tabId, {
            code:      css,
            cssOrigin: 'user',
            allFrames: true,
        });
        appliedCss.delete(tabId);
    } catch (e) {
        console.warn('nightpanel: removeCSS failed for tab', tabId, e);
    }
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

async function applyToAllTabs(b) {
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
        injectTab(tab.id, b);
        injectMeta(tab.id);
    }
}

async function activate(b) {
    active     = true;
    brightness = b;
    // Register the meta-tag content script FIRST so new navigations that
    // race with our applyToAllTabs pass still get the early-injection path.
    await registerMetaScript();
    await applyToAllTabs(b);
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

// Clean up our per-tab state when a tab closes.
browser.tabs.onRemoved.addListener((tabId) => {
    appliedCss.delete(tabId);
});

// ── Boot ──────────────────────────────────────────────────────────────────

connect();
