# extensions.gnome.org submission checklist — `nightpanel@nightpanel`

**STATUS: prepared for review, NOT submitted.** Per project memory (Flathub burned us; always prep + checklist, user clicks submit), the actual upload at https://extensions.gnome.org/upload/ is Greg's call after reviewing the items below.

**Artifact:** `packaging/extensions-gnome-org/nightpanel@nightpanel-v2.zip` (6.2 KB, three files).

---

## Pre-submission compliance review

Source: https://gjs.guide/extensions/review-guidelines/review-guidelines.html (e.g.o. review guidelines, last checked against this checklist 2026-05-26).

| Guideline | Status | Notes |
|---|---|---|
| **License declared** | ⚠️ TODO | Add `"license": "GPL-3.0-or-later"` to metadata.json before submit. Currently absent. (Not always required but recommended.) |
| **Open source, no obfuscation** | ✅ | extension.js is hand-written ES module, 139 lines, readable. |
| **`shell-version` matches what's tested** | ⚠️ | Currently declares `["45","46","47","48"]`. Greg has tested on 48.7 only. Reviewers may flag broad compatibility claims without evidence. **Decision needed:** narrow to `["48"]` for first submission, or leave broad and trust the API surface used (PanelMenu.Button, addToStatusArea, Gio.FileMonitor — all stable since 45)? |
| **No external network calls** | ✅ | Extension only reads `~/.config/nightpanel/nightpanel-active` and spawns `~/.local/bin/nightpanel-toggle`. |
| **No web requests, telemetry, analytics** | ✅ | None. |
| **Spawns external binaries** | ⚠️ disclosure | Spawns `~/.local/bin/nightpanel-toggle`. Reviewers sometimes ask why a panel extension needs to exec; the answer in the description is "companion to the Nightpanel desktop app — the toggle script is the orchestrator that drives every adapter." Be ready to explain in the review comments. |
| **No use of deprecated APIs** | ✅ | Uses GNOME 45+ ES-module Extension class, `resource:///` imports — current as of GNOME 48. |
| **Reasonable description** | ✅ | metadata.json description tightened to explain what it does + that it's a companion to the desktop app. |
| **`url` field set** | ✅ | https://github.com/gregfelice/nightpanel |
| **No third-party libraries bundled** | ✅ | Vanilla ESM imports from `resource:///org/gnome/shell/...` only. |
| **Cleanup on disable()** | ✅ | `disable()` cancels file monitor, destroys panel button, restores hidden actors. |

## Decisions Greg needs to make before clicking submit

1. **License field.** Add `"license": "GPL-3.0-or-later"` to metadata.json? (Recommended — match the rest of the project.) If yes, edit `src/nightpanel/shell-extension/nightpanel@nightpanel/metadata.json` and re-zip with `python3 -m zipfile -c packaging/extensions-gnome-org/nightpanel@nightpanel-v2.zip <files>`.

2. **`shell-version` scope.** Submit broad (`["45","46","47","48"]`) or narrow (`["48"]`)? Narrow is safer for first submission; broaden in v3 after evidence-based testing.

3. **Description tone.** Current: "Panel button to toggle the Nightpanel system-wide dark-mode orchestrator." Reviewers occasionally ask for plainer language. Acceptable as-is in my judgment, but Greg's call.

## Submission steps (when Greg is ready)

1. Visit https://extensions.gnome.org/upload/
2. Sign in with the e.g.o. account (likely the same as the gregfelice GitHub identity if registered).
3. Upload `packaging/extensions-gnome-org/nightpanel@nightpanel-v2.zip`.
4. Set the version label, target shell versions (must match metadata.json).
5. Submit for review.
6. **Watch the email + e.g.o. dashboard for reviewer feedback.** Be polite, be quick to respond — per project memory, the prior Flathub interaction went south due to a bad-tempered moderator + an undetected guideline gap. e.g.o. reviewers are generally friendlier than Flathub's but the same discipline applies.

## What to do if rejected

1. Read the rejection comment carefully. Do not respond in anger.
2. Fix the cited issue in `src/nightpanel/shell-extension/nightpanel@nightpanel/`.
3. Bump `version` in metadata.json.
4. Rebuild the ZIP (`python3 ./packaging/extensions-gnome-org/build.py` — TODO: write this helper as a follow-up).
5. Resubmit through the e.g.o. dashboard (revision flow, not a fresh submission).

## Rollback / unpublish

If after submission and approval there's a critical bug:
- Pulling the extension from e.g.o. is irreversible from the maintainer side; only an admin can hard-delete.
- The safer path: publish a fixed v3 immediately. Old version stays installable but new installs get v3.
