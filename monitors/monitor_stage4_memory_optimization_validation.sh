#!/usr/bin/env bash
set -u

REPO="${SPINELLI_REPO:-/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro}"
SESSION="${SPINELLI_OPT_TMUX:-spinelli-stage4-memory-opt}"
LINK="$REPO/results/stage4_memory_optimization_validation_latest"
REFRESH="${SPINELLI_MONITOR_REFRESH:-10}"

line(){ printf '%*s\n' 100 ''|tr ' ' '='; }
subline(){ printf '%*s\n' 100 ''|tr ' ' '-'; }

find_python_pid() {
  ps -eo pid=,comm=,args= |
  awk '
    $2 ~ /^python/ &&
    index($0,"run_stage4_streaming_export_regression.py") {
      print $1
      exit
    }
  '
}

find_wrapper_pid() {
  ps -eo pid=,comm=,args= |
  awk '
    $2 == "bash" &&
    index($0,"run_stage4_memory_optimization_validation.sh") {
      print $1
      exit
    }
  '
}

snapshot() {
  pid="$(find_python_pid)"
  wrapper="$(find_wrapper_pid)"
  root=""; active_log=""; report=""; current_n="none"

  if [[ -L "$LINK" ]]; then
    root="$(readlink -f "$LINK" 2>/dev/null||true)"
    [[ -n "$root" ]] &&
      report="$root/stage4_memory_optimization_validation_report.txt"
    if [[ -n "$root" ]]; then
      active_log="$(
        find "$root" -type f -name 'stage4_streaming_N*.run.log' \
          -printf '%T@ %p\n' 2>/dev/null |
        sort -nr | head -n1 | sed 's/^[^ ]* //'
      )"
    fi
  fi

  if [[ -n "$pid" ]]; then
    current_n="$(
      tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null |
      sed -n 's/.*--target-n[[:space:]]\+\([^[:space:]]\+\).*/\1/p'
    )"
  fi

  state="NOT_STARTED"; interpretation="No validation run detected."
  if [[ -n "$pid" ]]; then
    state="RUNNING"
    interpretation="Actual optimized Python regression is active."
  elif [[ -f "$report" ]] &&
       grep -q '^STAGE4_MEMORY_OPTIMIZATION_VALIDATION_RESULT=PASS$' \
         "$report"; then
    state="COMPLETED_PASS"
    interpretation="Both regressions and the memory gate completed."
  elif [[ -n "$wrapper" ]]; then
    state="WRAPPER_ACTIVE"
    interpretation="Wrapper active between cases or during postprocessing."
  elif [[ -n "$root" ]]; then
    state="STOPPED_OR_FAILED"
    interpretation="Output exists without an active process or final PASS."
  elif tmux has-session -t "$SESSION" 2>/dev/null; then
    state="TMUX_EXISTS_NO_RUN"
    interpretation="Tmux exists but validation has not started."
  fi

  clear 2>/dev/null||true
  line
  echo " SPINELLI STAGE 4 MEMORY OPTIMIZATION VALIDATION"
  line
  printf ' Time:              %s\n' "$(date -Is)"
  printf ' State:             %s\n' "$state"
  printf ' Interpretation:    %s\n' "$interpretation"
  printf ' Current N:         %s\n' "${current_n:-unknown}"
  printf ' Root:              %s\n' "${root:-not created}"
  printf ' Python PID:        %s\n' "${pid:-not running}"
  printf ' Wrapper PID:       %s\n' "${wrapper:-not running}"
  printf ' Tmux:              %s\n' \
    "$(tmux has-session -t "$SESSION" 2>/dev/null && echo PRESENT || echo ABSENT)"
  line

  echo " SYSTEM MEMORY"; subline
  free -h
  awk '
    /MemAvailable:/ {ma=$2}
    /SwapTotal:/ {st=$2}
    /SwapFree:/ {sf=$2}
    END {
      printf " MemAvailable: %.2f GiB\n",ma/1048576
      printf " Swap used:    %.2f GiB of %.2f GiB\n",(st-sf)/1048576,st/1048576
    }' /proc/meminfo

  if [[ -n "$pid" && -r "/proc/$pid/status" ]]; then
    echo; echo " ACTIVE PYTHON PROCESS"; subline
    ps -p "$pid" -o pid,ppid,comm,state,etime,%cpu,%mem,rss,vsz,args
    awk '
      /^VmRSS:/{r=$2}
      /^VmSwap:/{s=$2}
      /^Threads:/{t=$2}
      END {
        printf " VmRSS: %.2f GiB\n VmSwap: %.2f GiB\n Threads: %s\n",r/1048576,s/1048576,t
      }' "/proc/$pid/status"
  fi

  echo; echo " RECENT PAGING"; subline
  command -v vmstat >/dev/null 2>&1 && vmstat 1 2|tail -n3 || true

  echo; echo " ACTIVE/NEWEST LOG"; subline
  [[ -f "$active_log" ]] && tail -n34 "$active_log" || echo " No case log."

  echo; echo " TMUX PANE"; subline
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux capture-pane -pt "$SESSION":0 -S -24 2>/dev/null|tail -n24
  else
    echo " Tmux absent."
  fi
  line
}

case "${1:-}" in
 --watch) while true; do snapshot; sleep "$REFRESH"; done ;;
 "") snapshot ;;
 *) echo "Usage: $0 [--watch]" >&2; exit 2 ;;
esac
