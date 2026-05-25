'use strict';

// nightpanel bridge — background script

const HOST     = 'nightpanel';
const STYLE_ID = 'nightpanel-palette';

// ── CSS ────────────────────────────────────────────────────────────────────
// Invert + hue-rotate the whole page (black bg, legible text).
// Images and video are double-inverted back to normal.
// brightness() is injected at apply-time from the command payload.

function makeCss(brightness) {
    return `
html {
  color-scheme: light !important;
  filter: invert(1) hue-rotate(180deg) brightness(${brightness}) contrast(1.05) !important;
}
img, video, canvas, iframe, picture, embed, object {
  filter: invert(1) hue-rotate(180deg) !important;
}
::selection {
  background-color: #1A3020 !important;
  color: #26DE81 !important;
}
`;
}

function makeInjectCode(brightness) {
    const css = JSON.stringify(makeCss(brightness));
    return `(function() {
  let s = document.getElementById('${STYLE_ID}');
  if (!s) {
    s = document.createElement('style');
    s.id = '${STYLE_ID}';
    (document.head || document.documentElement).appendChild(s);
  }
  s.textContent = ${css};
})();`;
}

const REMOVE_CODE = `(function() {
  const s = document.getElementById('${STYLE_ID}');
  if (s) s.remove();
})();`;

// ── State ──────────────────────────────────────────────────────────────────

let active     = false;
let brightness = 0.9;
let port       = null;

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

// ── CSS apply / remove ─────────────────────────────────────────────────────

async function injectTab(tabId, b) {
    try {
        await browser.tabs.executeScript(tabId, {
            code:      makeInjectCode(b),
            allFrames: true,
            runAt:     'document_start',
        });
    } catch (_) {}
}

async function removeTab(tabId) {
    try {
        await browser.tabs.executeScript(tabId, {
            code:      REMOVE_CODE,
            allFrames: true,
        });
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

// ── Boot ──────────────────────────────────────────────────────────────────

connect();
