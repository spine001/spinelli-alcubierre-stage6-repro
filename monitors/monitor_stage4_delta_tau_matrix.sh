#!/usr/bin/env bash
set -u

REPO="${SPINELLI_REPO:-/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro}"
SESSION="${SPINELLI_DTAU_TMUX:-spinelli-stage4-N71-dtau}"
LINK="$REPO/results/stage4_n71_delta_tau_matrix_latest"
REFRESH="${SPINELLI_MONITOR_REFRESH:-10}"

line(){ printf '%*s\n' 100 '' | tr ' ' '='; }
subline(){ printf '%*s\n' 100 '' | tr ' ' '-'; }

find_python_pid() {
  ps -eo pid=,comm=,args= |
  awk '
    $2 ~ /^python/ && index($0,"run_stage4_n71_delta_tau_case.py") {
      print $1
      exit
    }
  '
}

find_wrapper_pid() {
  ps -eo pid=,comm=,args= |
  awk '
    $2 == "bash" && index($0,"run_stage4_n71_delta_tau_matrix.sh") {
      print $1
      exit
    }
  '
}

snapshot() {
  local pid wrapper matrix report master_log active_log state interpretation current_tau
  pid="$(find_python_pid)"
  wrapper="$(find_wrapper_pid)"
  matrix=""
  report=""
  master_log=""
  active_log=""
  current_tau="none"

  if [[ -L "$LINK" ]]; then
    matrix="$(readlink -f "$LINK" 2>/dev/null || true)"
    [[ -n "$matrix" ]] && report="$matrix/stage4_n71_delta_tau_matrix_report.txt"
    [[ -n "$matrix" ]] && master_log="$matrix/stage4_n71_delta_tau_matrix.run.log"
    if [[ -n "$matrix" ]]; then
      active_log="$(
        find "$matrix" -type f -name 'stage4_n71_dtau_*.run.log' \
          -printf '%T@ %p\n' 2>/dev/null |
        sort -nr |
        head -n1 |
        sed 's/^[^ ]* //'
      )"
    fi
  fi

  if [[ -n "$pid" ]]; then
    current_tau="$(
      tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null |
      sed -n 's/.*--delta-tau[[:space:]]\+\([^[:space:]]\+\).*/\1/p'
    )"
  fi

  state="NOT_STARTED"
  interpretation="No matrix directory or active process detected."
  if [[ -n "$pid" ]]; then
    state="RUNNING"
    interpretation="A DELTA_TAU case is running in the actual Python process."
  elif [[ -f "$report" ]] &&
       grep -q '^STAGE4_N71_DELTA_TAU_MATRIX_RESULT=PASS$' "$report"; then
    state="COMPLETED_PASS"
    interpretation="The complete sensitivity matrix passed."
  elif [[ -n "$wrapper" ]]; then
    state="WRAPPER_ACTIVE"
    interpretation="The wrapper is active between cases or during postprocessing."
  elif [[ -n "$matrix" ]]; then
    state="STOPPED_OR_FAILED"
    interpretation="A matrix directory exists but no active process or final PASS was found."
  elif tmux has-session -t "$SESSION" 2>/dev/null; then
    state="TMUX_EXISTS_NO_RUN"
    interpretation="The tmux session exists, but the matrix has not started."
  fi

  clear 2>/dev/null || true
  line
  echo " SPINELLI STAGE 4 N71 DELTA_TAU MATRIX MONITOR"
  line
  printf ' Time:              %s\n' "$(date -Is)"
  printf ' State:             %s\n' "$state"
  printf ' Interpretation:    %s\n' "$interpretation"
  printf ' Current DELTA_TAU: %s\n' "${current_tau:-unknown}"
  printf ' Matrix directory:  %s\n' "${matrix:-not created}"
  printf ' Python PID:        %s\n' "${pid:-not running}"
  printf ' Wrapper PID:       %s\n' "${wrapper:-not running}"
  printf ' Tmux:              %s\n' \
    "$(tmux has-session -t "$SESSION" 2>/dev/null && echo PRESENT || echo ABSENT)"
  line

  echo " SYSTEM MEMORY"
  subline
  free -h
  awk '
    /MemAvailable:/ {ma=$2}
    /SwapTotal:/ {st=$2}
    /SwapFree:/ {sf=$2}
    END {
      printf " MemAvailable: %.2f GiB\n",ma/1048576
      printf " Swap used:    %.2f GiB of %.2f GiB\n",(st-sf)/1048576,st/1048576
    }
  ' /proc/meminfo

  if [[ -n "$pid" && -r "/proc/$pid/status" ]]; then
    echo
    echo " ACTIVE PYTHON CASE"
    subline
    ps -p "$pid" -o pid,ppid,comm,state,etime,%cpu,%mem,rss,vsz,args
    awk '
      /^VmRSS:/ {r=$2}
      /^VmSwap:/ {s=$2}
      /^Threads:/ {t=$2}
      END {
        printf " VmRSS:   %.2f GiB\n",r/1048576
        printf " VmSwap:  %.2f GiB\n",s/1048576
        printf " Threads: %s\n",t
      }
    ' "/proc/$pid/status"
  fi

  echo
  echo " RECENT PAGING"
  subline
  command -v vmstat >/dev/null 2>&1 && vmstat 1 2 | tail -n3 || true

  echo
  echo " ACTIVE/NEWEST CASE LOG"
  subline
  if [[ -f "$active_log" ]]; then
    echo " $active_log"
    tail -n30 "$active_log"
  else
    echo " No case log exists."
  fi

  echo
  echo " MASTER MATRIX LOG"
  subline
  if [[ -f "$master_log" ]]; then
    tail -n24 "$master_log"
  else
    echo " No master log exists."
  fi

  echo
  echo " TMUX PANE"
  subline
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux capture-pane -pt "$SESSION":0 -S -24 2>/dev/null | tail -n24
  else
    echo " Tmux session absent."
  fi
  line
}

case "${1:-}" in
  --watch)
    while true; do snapshot; sleep "$REFRESH"; done
    ;;
  "")
    snapshot
    ;;
  *)
    echo "Usage: $0 [--watch]" >&2
    exit 2
    ;;
esac
