#!/usr/bin/env bash
# Security scan runner for Ieogagi.
#
# Usage:  scripts/security_scan.sh [--quick] [-h|--help]
#   (default)  run every tool: ruff, bandit, custom Semgrep, registry Semgrep,
#              pip-audit, npm audit, npm lint
#   --quick    run only ruff, bandit and custom Semgrep (offline, fast, for pre-push)
#
# Reports are written to security/reports/<YYYY-MM-DD_HHMM>/ (git-ignored).
# Exit code: 0 = every step ran and found nothing, 1 = findings, 2 = usage error, 3 = a tool failed
#   (abnormal exit code, any Semgrep error entry, fatal error or missing report fields),
#   4 = nothing found but a step was skipped (tool missing, offline, no frontend).
#   Precedence 3 > 1 > 4 > 0: a failed tool means the result is unknown, and a skip is not a pass.
#
# Semgrep registry packs (p/python, p/secrets, ...) are fetched at scan time only.
# NEVER copy registry rules into this repository (Semgrep Rules License).

set -euo pipefail

QUICK=0
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    -h | --help)
      sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "알 수 없는 옵션: $arg (사용법: scripts/security_scan.sh [--quick])" >&2
      exit 2
      ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_BIN="$ROOT/backend/.venv/bin"
STAMP="$(date +%Y-%m-%d_%H%M)"
OUT="$ROOT/security/reports/$STAMP"
RESULTS="$OUT/.results.tsv"
mkdir -p "$OUT"
: >"$RESULTS"
ln -sfn "$STAMP" "$ROOT/security/reports/latest"

PY="$(command -v python3 || true)"
[ -n "$PY" ] || PY="$VENV_BIN/python"

RC=0 # exit code of the last run_tool call

# tool_path <name>: prefer the project venv, fall back to PATH, print nothing if missing.
tool_path() {
  if [ -x "$VENV_BIN/$1" ]; then
    echo "$VENV_BIN/$1"
  else
    command -v "$1" || true
  fi
}

# record <name> <status> <count> <note>: append one row to the summary table.
record() {
  printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >>"$RESULTS"
}

# run_tool <stdout-file> <stderr-file> <cmd...>: run without aborting the script, keep exit code in RC.
run_tool() {
  local out="$1" err="$2"
  shift 2
  RC=0
  "$@" >"$out" 2>"$err" || RC=$?
}

# count_json <kind> <file>: print the number of findings, or "error <reason>" when the
# report is not JSON, lacks the fields the tool always writes, or carries a fatal error.
count_json() {
  "$PY" -I - "$1" "$2" <<'PY'
import json
import sys

kind, path = sys.argv[1], sys.argv[2]


def fail(reason):
    print("error " + reason)
    sys.exit(0)


try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
except (OSError, ValueError):
    fail("JSON 아님")
if kind == "ruff":
    if not isinstance(data, list):
        fail("목록 형식 아님")
    total = len(data)
elif kind == "bandit-loc":
    total = data.get("metrics", {}).get("_totals", {}).get("loc", -1) if isinstance(data, dict) else -1
elif not isinstance(data, dict):
    fail("객체 형식 아님")
elif kind in ("bandit", "semgrep"):
    if not isinstance(data.get("results"), list) or not isinstance(data.get("errors"), list):
        fail("results·errors 필드 없음")
    # Any "errors" entry (Semgrep warn-level parse errors and timeouts included) means part of the input
    # was not scanned, so every level counts.
    if data["errors"]:
        fail("도구 오류 %d건" % len(data["errors"]))
    total = len(data["results"])
elif kind == "pip-audit":
    if not isinstance(data.get("dependencies"), list):
        fail("dependencies 필드 없음")
    total = sum(len(dep.get("vulns", [])) for dep in data["dependencies"])
elif kind == "npm-audit":
    # npm writes {"error": {...}} with exit 1 when the audit itself failed.
    if "error" in data:
        err = data["error"]
        fail("npm 오류 " + str(err.get("code", "?") if isinstance(err, dict) else "?"))
    total = data.get("metadata", {}).get("vulnerabilities", {}).get("total")
    if not isinstance(total, int):
        fail("metadata.vulnerabilities.total 필드 없음")
else:
    fail("알 수 없는 종류")
print(total)
PY
}

# finish_json <name> <kind> <file> <report-name> <ok-codes>: turn RC + JSON output into a summary row.
# <ok-codes> = exit codes that mean "ran normally" ("0 1" when 1 means findings). Any other code,
# an unusable report, or exit 1 with zero findings (tool failed but still wrote JSON) is an ERROR.
finish_json() {
  local name="$1" kind="$2" file="$3" report="$4" ok_codes=" $5 " count
  local log="${report%.json}.stderr.log"
  count="$(count_json "$kind" "$file")"
  if [[ "$ok_codes" != *" $RC "* ]]; then
    record "$name" ERROR "-" "비정상 종료(exit $RC), $log 확인"
  elif [[ "$count" == error* ]]; then
    record "$name" ERROR "-" "${count#error }(exit $RC), $log 확인"
  elif [ "$RC" -eq 1 ] && [ "$count" -eq 0 ]; then
    record "$name" ERROR "-" "발견 0건인데 exit 1, $log 확인"
  elif [ "$count" -gt 0 ]; then
    record "$name" FOUND "$count" "$report"
  else
    record "$name" OK 0 "$report"
  fi
}

# online: true when semgrep.dev:443 is reachable (needed by registry packs, pip-audit, npm audit).
ONLINE=0
if "$PY" -I -c "import socket; socket.create_connection(('semgrep.dev', 443), 4).close()" 2>/dev/null; then
  ONLINE=1
fi

echo "리포트 폴더: security/reports/$STAMP"

# 1. ruff -------------------------------------------------------------------------------------
RUFF="$(tool_path ruff)"
if [ -z "$RUFF" ]; then
  record ruff SKIP "-" "ruff 없음 (make setup)"
else
  echo "[1] ruff"
  run_tool "$OUT/ruff.json" "$OUT/ruff.stderr.log" "$RUFF" check backend --no-cache --output-format json
  finish_json ruff ruff "$OUT/ruff.json" ruff.json "0 1"
fi

# 2. bandit -----------------------------------------------------------------------------------
BANDIT="$(tool_path bandit)"
if [ -z "$BANDIT" ]; then
  record bandit SKIP "-" "bandit 없음 (make setup)"
elif [ ! -d backend/app ]; then
  record bandit SKIP "-" "backend/app 없음"
else
  echo "[2] bandit"
  run_tool "$OUT/bandit.json" "$OUT/bandit.stderr.log" "$BANDIT" -q -r backend/app -c backend/pyproject.toml -f json
  finish_json bandit bandit "$OUT/bandit.json" bandit.json "0 1"
  run_tool "$OUT/bandit.txt" "$OUT/bandit-txt.stderr.log" "$BANDIT" -r backend/app -c backend/pyproject.toml -f txt
fi

# 3. semgrep custom rules ---------------------------------------------------------------------
SEMGREP="$(tool_path semgrep)"
if [ -z "$SEMGREP" ]; then
  record "semgrep(custom)" SKIP "-" "semgrep 없음 (make setup)"
elif [ ! -d backend/app ]; then
  record "semgrep(custom)" SKIP "-" "backend/app 없음"
else
  # Frontend code is scanned too (the contest may count it); JS rules live in frontend.yml.
  CUSTOM_TARGETS=(backend/app)
  [ -d frontend/src ] && CUSTOM_TARGETS+=(frontend/src)
  echo "[3] semgrep 자체 규칙 (security/semgrep): ${CUSTOM_TARGETS[*]}"
  run_tool "$OUT/semgrep-custom.json" "$OUT/semgrep-custom.stderr.log" \
    "$SEMGREP" --config security/semgrep --json --metrics=off --disable-version-check "${CUSTOM_TARGETS[@]}"
  finish_json "semgrep(custom)" semgrep "$OUT/semgrep-custom.json" semgrep-custom.json 0
fi

if [ "$QUICK" -eq 0 ]; then
  # 4. semgrep registry packs (fetched at scan time, never stored in the repo) ----------------
  if [ -z "$SEMGREP" ]; then
    record "semgrep(registry-be)" SKIP "-" "semgrep 없음"
  elif [ "$ONLINE" -eq 0 ]; then
    record "semgrep(registry-be)" SKIP "-" "오프라인: 네트워크 필요"
  elif [ ! -d backend/app ]; then
    record "semgrep(registry-be)" SKIP "-" "backend/app 없음"
  else
    echo "[4a] semgrep 공식 팩 (backend): p/python p/secrets p/owasp-top-ten"
    run_tool "$OUT/semgrep-registry-backend.json" "$OUT/semgrep-registry-backend.stderr.log" \
      "$SEMGREP" --config p/python --config p/secrets --config p/owasp-top-ten \
      --json --metrics=off --disable-version-check backend/app
    finish_json "semgrep(registry-be)" semgrep "$OUT/semgrep-registry-backend.json" semgrep-registry-backend.json 0
  fi

  if [ -z "$SEMGREP" ]; then
    record "semgrep(registry-fe)" SKIP "-" "semgrep 없음"
  elif [ ! -d frontend/src ]; then
    record "semgrep(registry-fe)" SKIP "-" "frontend/src 없음"
  elif [ "$ONLINE" -eq 0 ]; then
    record "semgrep(registry-fe)" SKIP "-" "오프라인: 네트워크 필요"
  else
    echo "[4b] semgrep 공식 팩 (frontend): p/javascript p/react p/secrets"
    run_tool "$OUT/semgrep-registry-frontend.json" "$OUT/semgrep-registry-frontend.stderr.log" \
      "$SEMGREP" --config p/javascript --config p/react --config p/secrets \
      --json --metrics=off --disable-version-check frontend/src
    finish_json "semgrep(registry-fe)" semgrep "$OUT/semgrep-registry-frontend.json" semgrep-registry-frontend.json 0
  fi

  # 5. pip-audit (dependency CVEs) ------------------------------------------------------------
  PIP_AUDIT="$(tool_path pip-audit)"
  if [ -z "$PIP_AUDIT" ]; then
    record pip-audit SKIP "-" "pip-audit 없음 (make setup)"
  elif [ ! -f backend/requirements.lock ]; then
    record pip-audit SKIP "-" "backend/requirements.lock 없음"
  elif [ "$ONLINE" -eq 0 ]; then
    record pip-audit SKIP "-" "오프라인: 네트워크 필요"
  else
    echo "[5] pip-audit (requirements.lock)"
    run_tool "$OUT/pip-audit.json" "$OUT/pip-audit.stderr.log" \
      "$PIP_AUDIT" -r backend/requirements.lock --progress-spinner off -f json
    finish_json pip-audit pip-audit "$OUT/pip-audit.json" pip-audit.json "0 1"
  fi

  # 6. npm audit ------------------------------------------------------------------------------
  if [ ! -f frontend/package.json ]; then
    record npm-audit SKIP "-" "frontend/package.json 없음"
  elif [ ! -f frontend/package-lock.json ]; then
    record npm-audit SKIP "-" "frontend/package-lock.json 없음"
  elif [ "$ONLINE" -eq 0 ]; then
    record npm-audit SKIP "-" "오프라인: 네트워크 필요"
  else
    echo "[6] npm audit (frontend, dev 의존성 제외)"
    run_tool "$OUT/npm-audit.json" "$OUT/npm-audit.stderr.log" npm --prefix frontend audit --omit=dev --json
    finish_json npm-audit npm-audit "$OUT/npm-audit.json" npm-audit.json "0 1"
  fi

  # 7. eslint via npm run lint ----------------------------------------------------------------
  if [ ! -f frontend/package.json ]; then
    record npm-lint SKIP "-" "frontend/package.json 없음"
  elif [ ! -d frontend/node_modules ]; then
    record npm-lint SKIP "-" "node_modules 없음 (npm ci 먼저)"
  else
    echo "[7] npm run lint (frontend)"
    run_tool "$OUT/npm-lint.txt" "$OUT/npm-lint.stderr.log" npm --prefix frontend run lint
    case "$RC" in # eslint: 1 = lint findings, anything else = crash or bad config
      0) record npm-lint OK 0 "npm-lint.txt" ;;
      1) record npm-lint FOUND "-" "exit 1, npm-lint.txt 확인" ;;
      *) record npm-lint ERROR "-" "비정상 종료(exit $RC), npm-lint.stderr.log 확인" ;;
    esac
  fi
fi

# Exit code, later checks override earlier ones: 4 = clean but a step was skipped, 1 = findings, 3 = a tool failed.
EXIT_CODE=0
grep -q $'\tSKIP\t' "$RESULTS" && EXIT_CODE=4
grep -q $'\tFOUND\t' "$RESULTS" && EXIT_CODE=1
grep -q $'\tERROR\t' "$RESULTS" && EXIT_CODE=3

# Summary -------------------------------------------------------------------------------------
{
  echo
  echo "=== 보안 점검 요약 ($STAMP, mode: $([ "$QUICK" -eq 1 ] && echo quick || echo full)) ==="
  printf '%-22s %-6s %-6s %s\n' TOOL STATUS COUNT NOTE
  printf '%-22s %-6s %-6s %s\n' ---------------------- ------ ------ ----
  while IFS=$'\t' read -r name status count note; do
    printf '%-22s %-6s %-6s %s\n' "$name" "$status" "$count" "$note"
  done <"$RESULTS"
  [ "$EXIT_CODE" -ne 4 ] || printf '\n%s\n' "결과 불완전: 건너뛴 도구 있음 (SKIP 줄 확인). 건너뛴 점검은 통과가 아니므로 종료 코드 4로 끝냅니다."
  if [ -f "$OUT/bandit.json" ]; then
    echo
    echo "분석 대상 코드 줄 수(bandit 기준, backend/app): $(count_json bandit-loc "$OUT/bandit.json")"
  fi
  if [ -d frontend/src ]; then
    # Frontend may count toward the contest's build-line denominator too (non-blank JS/JSX lines).
    FE_LINES="$(find frontend/src -type f \( -name '*.js' -o -name '*.jsx' \) -exec cat {} + | grep -cv '^[[:space:]]*$' || true)"
    echo "프론트엔드 코드 줄 수(빈 줄 제외, frontend/src *.js·*.jsx): $FE_LINES"
  fi
  echo "리포트: security/reports/$STAMP/ (최신: security/reports/latest)"
} | tee "$OUT/summary.txt"

exit "$EXIT_CODE"
