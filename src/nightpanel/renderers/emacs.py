# SPDX-License-Identifier: GPL-3.0-or-later
"""Render an Emacs colorscheme from a Palette.

Emits a standalone theme file using `deftheme` + `custom-theme-set-faces`,
mapping Palette slots onto the standard Emacs face set. The file is
self-contained — drop it into ~/.emacs.d/themes/ and `M-x load-theme RET
nightpanel`.
"""

from __future__ import annotations

from ..palette import Palette


def render(p: Palette) -> str:
    return f""";;; nightpanel-theme.el --- Saab instrument cluster colorscheme  -*- lexical-binding: t -*-
;;; Commentary:
;;  Generated from nightpanel.palette — edit there, not here.
;;  Pure black canvas, instrument-scale green text, amber needle accents.
;;; Code:

(deftheme nightpanel "Saab instrument cluster — pure black, instrument green, amber needle.")

(custom-theme-set-faces 'nightpanel
  ;; ── Base ─────────────────────────────────────────────────────
  '(default                ((t (:background "{p.bg}"         :foreground "{p.fg}"))))
  '(cursor                 ((t (:background "{p.fg_amber}"))))
  '(region                 ((t (:background "{p.bg_select}"))))
  '(highlight              ((t (:background "{p.bg_select}"  :foreground "{p.fg_bright}"))))
  '(secondary-selection    ((t (:background "{p.bg_accent}"))))
  '(fringe                 ((t (:background "{p.bg}"         :foreground "{p.fg_dim}"))))
  '(vertical-border        ((t (:foreground "{p.border_q}"))))
  '(window-divider         ((t (:foreground "{p.border_q}"))))
  '(window-divider-first-pixel ((t (:foreground "{p.border_q}"))))
  '(window-divider-last-pixel  ((t (:foreground "{p.border_q}"))))

  ;; ── Line numbers ─────────────────────────────────────────────
  '(line-number              ((t (:foreground "{p.fg_dim}"   :background "{p.bg}"))))
  '(line-number-current-line ((t (:foreground "{p.fg_bright}" :background "{p.bg}" :weight bold))))

  ;; ── Mode line ────────────────────────────────────────────────
  '(mode-line              ((t (:background "{p.bg_header}" :foreground "{p.fg}"      :box nil))))
  '(mode-line-inactive     ((t (:background "{p.bg_header}" :foreground "{p.fg_dim}"  :box nil))))
  '(mode-line-emphasis     ((t (:foreground "{p.fg_bright}" :weight bold))))
  '(mode-line-highlight    ((t (:foreground "{p.fg_amber}"))))
  '(mode-line-buffer-id    ((t (:foreground "{p.fg_bright}" :weight bold))))

  ;; ── Header / tab line ────────────────────────────────────────
  '(header-line            ((t (:background "{p.bg_card}"   :foreground "{p.fg}"))))
  '(tab-line               ((t (:background "{p.bg_header}" :foreground "{p.fg_dim}"))))
  '(tab-bar                ((t (:background "{p.bg_header}" :foreground "{p.fg_dim}"))))
  '(tab-bar-tab            ((t (:background "{p.bg_card}"   :foreground "{p.fg}"))))
  '(tab-bar-tab-inactive   ((t (:background "{p.bg_header}" :foreground "{p.fg_dim}"))))

  ;; ── Minibuffer ───────────────────────────────────────────────
  '(minibuffer-prompt      ((t (:foreground "{p.fg_bright}" :weight bold))))

  ;; ── Search / isearch ─────────────────────────────────────────
  '(isearch                ((t (:background "{p.amber_warm}" :foreground "{p.bg}"     :weight bold))))
  '(isearch-fail           ((t (:background "{p.red}"        :foreground "{p.bg}"))))
  '(lazy-highlight         ((t (:background "{p.fg_amber}"   :foreground "{p.bg}"))))
  '(match                  ((t (:background "{p.fg_amber}"   :foreground "{p.bg}"))))

  ;; ── Messages ─────────────────────────────────────────────────
  '(error                  ((t (:foreground "{p.red}"        :weight bold))))
  '(warning                ((t (:foreground "{p.amber_warm}" :weight bold))))
  '(success                ((t (:foreground "{p.fg_bright}"  :weight bold))))
  '(shadow                 ((t (:foreground "{p.fg_dim}"))))

  ;; ── Links ────────────────────────────────────────────────────
  '(link                   ((t (:foreground "{p.fg_bright}"  :underline t))))
  '(link-visited           ((t (:foreground "{p.fg_mid}"     :underline t))))

  ;; ── font-lock (syntax) ───────────────────────────────────────
  '(font-lock-comment-face            ((t (:foreground "{p.fg_dim}"   :slant italic))))
  '(font-lock-comment-delimiter-face  ((t (:foreground "{p.fg_dim}"))))
  '(font-lock-doc-face                ((t (:foreground "{p.fg_mid}"   :slant italic))))
  '(font-lock-string-face             ((t (:foreground "{p.fg_amber}"))))
  '(font-lock-keyword-face            ((t (:foreground "{p.fg_bright}" :weight bold))))
  '(font-lock-builtin-face            ((t (:foreground "{p.fg_bright}"))))
  '(font-lock-function-name-face      ((t (:foreground "{p.fg_light}" :weight bold))))
  '(font-lock-variable-name-face      ((t (:foreground "{p.fg}"))))
  '(font-lock-type-face               ((t (:foreground "{p.fg_light}"))))
  '(font-lock-constant-face           ((t (:foreground "{p.amber_warm}"))))
  '(font-lock-preprocessor-face       ((t (:foreground "{p.fg_amber}"))))
  '(font-lock-warning-face            ((t (:foreground "{p.amber_warm}" :weight bold))))
  '(font-lock-negation-char-face      ((t (:foreground "{p.red}"))))

  ;; ── Show-paren / parens ──────────────────────────────────────
  '(show-paren-match       ((t (:foreground "{p.fg_bright}" :weight bold :underline t))))
  '(show-paren-mismatch    ((t (:background "{p.red}"       :foreground "{p.bg}"))))

  ;; ── Diffs / version control ──────────────────────────────────
  '(diff-added             ((t (:foreground "{p.fg_bright}" :background "{p.bg_select}"))))
  '(diff-removed           ((t (:foreground "{p.red}"))))
  '(diff-changed           ((t (:foreground "{p.fg_amber}"))))
  '(diff-header            ((t (:foreground "{p.fg_light}" :weight bold))))
  '(diff-file-header       ((t (:foreground "{p.fg_bright}" :weight bold))))
  '(diff-hunk-header       ((t (:foreground "{p.fg_amber}"))))

  ;; ── Completion / company / corfu (best-effort) ───────────────
  '(completions-common-part       ((t (:foreground "{p.fg_bright}" :weight bold))))
  '(completions-first-difference  ((t (:foreground "{p.fg_amber}"))))

  ;; ── org-mode (best-effort) ───────────────────────────────────
  '(org-level-1            ((t (:foreground "{p.fg_bright}" :weight bold))))
  '(org-level-2            ((t (:foreground "{p.fg_light}"  :weight bold))))
  '(org-level-3            ((t (:foreground "{p.fg}"        :weight bold))))
  '(org-level-4            ((t (:foreground "{p.fg_mid}"))))
  '(org-todo               ((t (:foreground "{p.amber_warm}" :weight bold))))
  '(org-done               ((t (:foreground "{p.fg_dim}"))))
  '(org-block              ((t (:background "{p.bg_card}"))))
  '(org-code               ((t (:foreground "{p.fg_amber}"))))
  '(org-verbatim           ((t (:foreground "{p.fg_amber}")))))

(provide-theme 'nightpanel)
;;; nightpanel-theme.el ends here
"""
