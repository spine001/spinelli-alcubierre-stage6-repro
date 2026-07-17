#!/usr/bin/env bash
set -u

REPO="${SPINELLI_REPO:-/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro}"
SESSION="${SPINELLI_N91_TMUX:-spinelli-stage4-N91}"
LINK="$REPO/results/stage4_revalidation_N91_optimized_latest"
REFRESH="${SPINELLI_MONITOR_REFRESH:-10}"

line(){ printf '%*s\n' 100 ''|tr ' ' '='; }
subline(){ printf '%*s\n' 100 ''|tr ' ' '-'; }

find_python_pid() {
  ps -eo pid=,comm=,args= |
  awk '
    $2 ~ /^python/ && index($0,"run_stage4_n91_optimized.py") {
      print $1
      exit
    }
  '
}

find_wrapper_pid() {
  ps -eo pid=,comm=,args= |
  awk '
    $2 == "bash" && index($0,"run_stage4_n91_optimized.sh") {
      print $1
      exit
    }
  '
}

snapshot() {
  pid="$(find_python_pid)"
  wrapper="$(find_wrapper_pid)"
  out=""; log=""; report=""; cell="none"

  if [[ -L "$LINK" ]]; then
    out="$(readlink -f "$LINK" 2>/dev/null||true)"
    [[ -n "$out" ]] && log="$out/stage4_n91_optimized.run.log"
    [[ -n "$out" ]] && report="$out/stage4_n91_four_grid_report.txt"
  fi

  if [[ -f "$log" ]]; then
    cell="$(
      grep '===== EXECUTE NOTEBOOK CELL' "$log" 2>/dev/null |
      tail -n1 |
      sed 's/.*CELL \([0-9][0-9]*\).*/\1/' ||
      true
    )"
  fi

  state="NOT_STARTED"; interpretation="No optimized N91 run detected."
  if [[ -n "$pid" ]]; then
    state="RUNNING"
    interpretation="The actual optimized N91 Python process is active."
  elif [[ -f "$report" ]] &&
       grep -q '^STAGE4_N91_OPTIMIZED_ANALYSIS_RESULT=PASS$' "$report"; then
    state="COMPLETED_PASS"
    interpretation="N91 and its four-grid analysis completed."
  elif [[ -f "$log" ]] &&
       grep -q '^RUN_EXIT_CODE=[1-9][0-9]*$' "$log"; then
    state="FAILED"
    interpretation="The N91 calculation returned a nonzero exit code."
  elif [[ -n "$wrapper" ]]; then
    state="WRAPPER_ACTIVE"
    interpretation="Wrapper active during startup or postprocessing."
  elif [[ -n "$out" ]]; then
    state="STOPPED_OR_FAILED"
    interpretation="Output exists without an active process or final PASS."
  elif tmux has-session -t "$SESSION" 2>/dev/null; then
    state="TMUX_EXISTS_NO_RUN"
    interpretation="Tmux exists, but N91 has not started."
  fi

  clear 2>/dev/null||true
  line
  echo " SPINELLI STAGE 4 OPTIMIZED N91 MONITOR"
  line
  printf ' Time:              %s\n' "$(date -Is)"
  printf ' State:             %s\n' "$state"
  printf ' Interpretation:    %s\n' "$interpretation"
  printf ' Current cell:      %s\n' "${cell:-unknown}"
  printf ' Output directory:  %s\n' "${out:-not created}"
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

  echo; echo " LAST LOG LINES"; subline
  [[ -f "$log" ]] && tail -n36 "$log" || echo " No run log."

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
