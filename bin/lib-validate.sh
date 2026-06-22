#!/usr/bin/env bash
# lib-validate.sh — validator helpers. VENDORED: this is the project's own copy.
#
# Sourced by bin/validate (and any other bin/ check script). Self-contained — no
# dependency on any shared repo. See the standard:
#   knowledge/best-practice/process-validation.md
#
# Contract:
#   ok "desc"     — a check passed
#   fail "desc"   — a check failed (say what's missing)
#   skip "desc"   — a check doesn't apply here (say why)
#   summary       — print "--- N checks, M failures"
#   exit $FAILS   — caller exits with the failure count (0 = conformant)

# Counters the helpers maintain. The caller reads $FAILS for its exit code.
CHECKS=0
FAILS=0

# Colors, disabled when stdout is not a tty (clean logs in CI).
if [[ -t 1 ]]; then
    _RED=$'\e[31m'; _GREEN=$'\e[32m'; _YEL=$'\e[33m'; _RST=$'\e[0m'
else
    _RED=''; _GREEN=''; _YEL=''; _RST=''
fi

ok()   { CHECKS=$((CHECKS+1)); printf "  %sOK  %s%s\n" "$_GREEN" "$1" "$_RST"; }
fail() { CHECKS=$((CHECKS+1)); FAILS=$((FAILS+1)); printf "  %sFAIL%s %s\n" "$_RED" "$_RST" "$1"; }
skip() { CHECKS=$((CHECKS+1)); printf "  %sSKIP%s %s\n" "$_YEL" "$_RST" "$1"; }

# Convenience: ok/fail on a command's success. `check "desc" test -f foo`
check() {
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then ok "$desc"; else fail "$desc"; fi
}

summary() {
    echo
    if (( FAILS == 0 )); then
        printf "%s--- %d checks, 0 failures%s\n" "$_GREEN" "$CHECKS" "$_RST"
    else
        printf "%s--- %d checks, %d failures%s\n" "$_RED" "$CHECKS" "$FAILS" "$_RST"
    fi
}
