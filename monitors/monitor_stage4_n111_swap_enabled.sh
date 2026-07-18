#!/usr/bin/env bash
set -u

REPO="${SPINELLI_REPO:-/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro}"
SESSION="${SPINELLI_N111_TMUX:-spinelli-stage4-N111}"
LINK="$REPO/results/stage4_revalidation_N111_swap_enabled_latest"
REFRESH="${SPINELLI_MONITOR_REFRESH:-10}"

line(){ printf '%*s\n' 104 '' | tr ' ' '='; }
subline(){ printf '%*s\n' 104 '' | tr ' ' '-'; }

find_python_pid() {
  local output="${1:-}"
  ps -eo pid=,comm=,args= |
  awk -v output="$output" '
    $2 ~ /^python/ &&
    index($0, "run_stage4_n111_optimized_swap_enabled.py") &&
    (output == "" || index($0, output)) {
      print $1
      exit
    }
  '
}

snapshot() {
  OUT=""
  [[ -L "$LINK" ]] &&
    OUT="$(readlink -f "$LINK" 2>/dev/null || true)"

  LOG=""
  REPORT=""
  SAMPLES=""
  [[ -n "$OUT" ]] &&
    LOG="$OUT/stage4_n111_optimized_swap_enabled.run.log"
  [[ -n "$OUT" ]] &&
    REPORT="$OUT/stage4_n111_six_grid_report.txt"
  [[ -n "$OUT" ]] &&
    SAMPLES="$OUT/stage4_n111_resource_samples.csv"

  PID="$(find_python_pid "$OUT" || true)"
  CELL="none"
  [[ -f "$LOG" ]] &&
    CELL="$(
      grep '===== EXECUTE NOTEBOOK CELL' "$LOG" |
      tail -n1 |
      sed 's/.*CELL \([0-9][0-9]*\).*/\1/' ||
      true
    )"

  STATE="NOT_STARTED"
  NOTE="No N111 run detected."
  if [[ -n "$PID" ]]; then
    STATE="RUNNING"
    NOTE="The actual N111 Python process is active."
  elif [[ -f "$REPORT" ]] &&
       grep -q '^STAGE4_N111_SIX_GRID_ANALYSIS_RESULT=PASS$' "$REPORT"; then
    STATE="COMPLETED_PASS"
    NOTE="N111 and its six-grid analysis completed."
  elif [[ -f "$LOG" ]] &&
       grep -q '^RUN_EXIT_CODE=[1-9][0-9]*$' "$LOG"; then
    STATE="FAILED"
    NOTE="N111 returned a nonzero exit code."
  elif [[ -n "$OUT" ]]; then
    STATE="STOPPED_OR_POSTPROCESSING"
    NOTE="Output exists without active Python or final analysis PASS."
  fi

  clear 2>/dev/null || true
  line
  echo " SPINELLI STAGE 4 N111 SWAP-ENABLED MONITOR"
  line
  printf ' Time:                %s\n' "$(date -Is)"
  printf ' State:               %s\n' "$STATE"
  printf ' Interpretation:      %s\n' "$NOTE"
  printf ' Current cell:        %s\n' "${CELL:-unknown}"
  printf ' Output directory:    %s\n' "${OUT:-not created}"
  printf ' Actual Python PID:   %s\n' "${PID:-not running}"
  printf ' Tmux:                %s\n' \
    "$(tmux has-session -t "$SESSION" 2>/dev/null &&
       echo PRESENT || echo ABSENT)"
  line

  echo " SYSTEM MEMORY AND SWAP"
  subline
  free -h
  swapon --show || true
  awk '
    /MemAvailable:/ {available=$2}
    /SwapTotal:/ {total=$2}
    /SwapFree:/ {free=$2}
    END {
      printf " MemAvailable: %.2f GiB\n", available/1048576
      printf " Swap used:    %.2f GiB of %.2f GiB\n",
        (total-free)/1048576, total/1048576
    }
  ' /proc/meminfo

  if [[ -n "$PID" && -r "/proc/$PID/status" ]]; then
    echo
    echo " ACTUAL PYTHON PROCESS"
    subline
    ps -p "$PID" \
      -o pid,ppid,comm,state,etime,%cpu,%mem,rss,vsz,args
    awk '
      /^VmRSS:/ {rss=$2}
      /^VmSwap:/ {swap=$2}
      /^VmSize:/ {size=$2}
      /^VmHWM:/ {hwm=$2}
      /^VmPeak:/ {peak=$2}
      /^Threads:/ {threads=$2}
      END {
        printf " VmRSS:       %.2f GiB\n", rss/1048576
        printf " VmSwap:      %.2f GiB\n", swap/1048576
        printf " RSS+Swap:    %.2f GiB\n", (rss+swap)/1048576
        printf " VmSize:      %.2f GiB\n", size/1048576
        printf " VmHWM:       %.2f GiB\n", hwm/1048576
        printf " VmPeak:      %.2f GiB\n", peak/1048576
        printf " Threads:     %s\n", threads
      }
    ' "/proc/$PID/status"
  fi

  echo
  echo " CURRENT PAGING RATE"
  subline
  vmstat 1 2 | tail -n3

  echo
  echo " RESOURCE SAMPLE PEAKS"
  subline
  if [[ -f "$SAMPLES" ]]; then
    awk -F, '
      NR > 1 {
        samples++
        if ($5+0 > rss) rss=$5+0
        if ($6+0 > swap) swap=$6+0
        if (($5+$6)+0 > combined) combined=($5+$6)+0
        if ($7+0 > size) size=$7+0
        if ($8+0 > hwm) hwm=$8+0
        if ($9+0 > peak) peak=$9+0
        if (min_available == 0 || $11+0 < min_available)
          min_available=$11+0
        if ($12+0 > system_swap) system_swap=$12+0
        if (first_in == "") first_in=$13+0
        if (first_out == "") first_out=$14+0
        last_in=$13+0
        last_out=$14+0
      }
      END {
        printf " Samples:                 %d\n", samples
        printf " Max VmRSS:               %.2f GiB\n", rss/1048576
        printf " Max VmSwap:              %.2f GiB\n", swap/1048576
        printf " Max RSS+Swap:            %.2f GiB\n", combined/1048576
        printf " Max VmSize:              %.2f GiB\n", size/1048576
        printf " Max VmHWM:               %.2f GiB\n", hwm/1048576
        printf " Max VmPeak:              %.2f GiB\n", peak/1048576
        printf " Min MemAvailable:        %.2f GiB\n", min_available/1048576
        printf " Max system swap used:    %.2f GiB\n", system_swap/1048576
        printf " pswpin delta pages:      %.0f\n", last_in-first_in
        printf " pswpout delta pages:     %.0f\n", last_out-first_out
      }
    ' "$SAMPLES"
  else
    echo " No resource samples yet."
  fi

  echo
  echo " LAST LOG LINES"
  subline
  [[ -f "$LOG" ]] &&
    tail -n36 "$LOG" ||
    echo " No run log."
  line
}

case "${1:-}" in
  --watch)
    while true; do
      snapshot
      sleep "$REFRESH"
    done
    ;;
  "")
    snapshot
    ;;
  *)
    echo "Usage: $0 [--watch]" >&2
    exit 2
    ;;
esac
