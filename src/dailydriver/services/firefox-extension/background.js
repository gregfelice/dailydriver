'use strict';

// nightpanel bridge — background script
//
// Connects to the native host (np-host.py) which watches np-command.json.
// When the orchestrator writes {action:"apply"} or {action:"revert"}, the
// host forwards it here and we inject/remove the nightpanel CSS palette.
//
// CSS is injected at cssOrigin:"user" — user stylesheets beat DarkReader's
// author-level !important rules, so our green/amber palette wins cleanly.

const HOST = 'nightpanel';

// ── Nightpanel palette CSS ─────────────────────────────────────────────────
// Targets pages where DarkReader has applied dark mode (data-darkreader-scheme).
// DarkReader handles the dark inversion; we tint its output with NP colors.
const NP_CSS = `
html[data-darkreader-scheme="dark"] body {
  background-color: #0A0A0A !important;
  color: #7DB890 !important;
}
html[data-darkreader-scheme="dark"] a,
html[data-darkreader-scheme="dark"] a:link {
  color: #B08030 !important;
}
html[data-darkreader-scheme="dark"] a:visited {
  color: #7DB890 !important;
}
html[data-darkreader-scheme="dark"] a:hover,
html[data-darkreader-scheme="dark"] a:focus {
  color: #26DE81 !important;
}
html[data-darkreader-scheme="dark"] code,
html[data-darkreader-scheme="dark"] pre,
html[data-darkreader-scheme="dark"] kbd,
html[data-darkreader-scheme="dark"] tt,
html[data-darkreader-scheme="dark"] samp {
  color: #26DE81 !important;
  background-color: #111111 !important;
}
html[data-darkreader-scheme="dark"] blockquote {
  border-left-color: #2E5040 !important;
  color: #5A8A6A !important;
}
html[data-darkreader-scheme="dark"] ::selection {
  background-color: #1A3020 !important;
  color: #26DE81 !important;
}
html[data-darkreader-scheme="dark"] ::-moz-selection {
  background-color: #1A3020 !important;
  color: #26DE81 !important;
}
`;

// ── State ──────────────────────────────────────────────────────────────────

let active = false;
let port   = null;

// ── Native host connection ─────────────────────────────────────────────────

function connect() {
    try {
        port = browser.runtime.connectNative(HOST);
        port.onMessage.addListener(onCommand);
        port.onDisconnect.addListener(() => {
            port = null;
            // Reconnect — host may have been replaced by orchestrator
            setTimeout(connect, 5000);
        });
    } catch (e) {
        // Native host not installed yet — retry later
        setTimeout(connect, 15000);
    }
}

function onCommand(cmd) {
    if (!cmd || typeof cmd.action !== 'string') return;
    if (cmd.action === 'apply')  activate();
    if (cmd.action === 'revert') deactivate();
}

// ── CSS apply / remove ─────────────────────────────────────────────────────

async function activate() {
    active = true;
    const tabs = await browser.tabs.query({});
    for (const tab of tabs) {
        if (isInjectable(tab.url)) injectTab(tab.id).catch(() => {});
    }
}

async function deactivate() {
    active = false;
    const tabs = await browser.tabs.query({});
    for (const tab of tabs) {
        if (isInjectable(tab.url)) removeTab(tab.id).catch(() => {});
    }
}

function isInjectable(url) {
    if (!url) return false;
    return !url.startsWith('about:') &&
           !url.startsWith('moz-extension:') &&
           !url.startsWith('chrome:') &&
           !url.startsWith('resource:');
}

function injectTab(tabId) {
    return browser.tabs.insertCSS(tabId, {
        code:      NP_CSS,
        cssOrigin: 'user',
        allFrames: false,
        runAt:     'document_start',
    });
}

function removeTab(tabId) {
    return browser.tabs.removeCSS(tabId, {
        code:      NP_CSS,
        cssOrigin: 'user',
        allFrames: false,
    });
}

// Re-inject on new page loads while nightpanel is active
browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (active && changeInfo.status === 'complete' && isInjectable(tab.url)) {
        injectTab(tabId).catch(() => {});
    }
});

// ── Boot ───────────────────────────────────────────────────────────────────

connect();
