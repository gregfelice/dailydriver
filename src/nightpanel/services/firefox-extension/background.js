'use strict';

// nightpanel bridge — background script

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
    const imgBrightness = (brightness * 0.95).toFixed(2);
    return `
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

/* Images: heavy desaturation + slight green tint so they harmonize */
img, video, canvas, iframe, picture, embed, object {
    filter: saturate(0.2) sepia(0.4) hue-rotate(60deg) brightness(${imgBrightness}) !important;
}

/* Selection: NP dark green bg, bright green text */
::selection {
    background-color: #1A3020 !important;
    color: #26DE81 !important;
}
`;
}

// ── State ──────────────────────────────────────────────────────────────────

let active     = false;
let brightness = 0.9;
let port       = null;
// Track the last-applied CSS per tab so we can removeCSS() with the same code.
const appliedCss = new Map();

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
    try {
        // Remove any previously-injected CSS for this tab so we don't pile up
        // multiple stylesheets across brightness changes.
        const previous = appliedCss.get(tabId);
        if (previous) {
            try {
                await browser.tabs.removeCSS(tabId, {
                    code:      previous,
                    cssOrigin: 'user',
                    allFrames: true,
                });
            } catch (_) {}
        }
        await browser.tabs.insertCSS(tabId, {
            code:      css,
            cssOrigin: 'user',          // beats inline !important from the page
            allFrames: true,
            runAt:     'document_start',
        });
        appliedCss.set(tabId, css);
    } catch (_) {}
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
    } catch (_) {}
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
        if (isInjectable(tab.url)) injectTab(tab.id, b);
    }
}

async function activate(b) {
    active     = true;
    brightness = b;
    await applyToAllTabs(b);
}

async function deactivate() {
    active = false;
    const tabs = await browser.tabs.query({});
    for (const tab of tabs) {
        if (isInjectable(tab.url)) removeTab(tab.id);
    }
}

// Re-inject on new page loads while active
browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (active && changeInfo.status === 'complete' && isInjectable(tab.url)) {
        injectTab(tabId, brightness);
    }
});

// Clean up our per-tab state when a tab closes.
browser.tabs.onRemoved.addListener((tabId) => {
    appliedCss.delete(tabId);
});

// ── Boot ──────────────────────────────────────────────────────────────────

connect();
