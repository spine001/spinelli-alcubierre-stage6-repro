#!/usr/bin/env bash
set -u

REPO="${SPINELLI_REPO:-/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro}"
SESSION="${SPINELLI_BATCH_TMUX:-spinelli-stage4-overnight}"
LINK="$REPO/results/stage4_overnight_batch_latest"
REFRESH="${SPINELLI_MONITOR_REFRESH:-10}"

line(){ printf '%*s\n' 108 '' | tr ' ' '='; }
subline(){ printf '%*s\n' 108 '' | tr ' ' '-'; }

active_process() {
  ps -eo pid=,comm=,args= |
  awk '
    $2 ~ /^python/ &&
    index($0, "run_stage4_overnight_batch_case.py") {
      print
      exit
    }
  '
}

snapshot() {
  ROOT=""
  [[ -L "$LINK" ]] &&
    ROOT="$(readlink -f "$LINK" 2>/dev/null || true)"

  PROCESS="$(active_process || true)"
  PID="$(awk '{print $1}' <<< "$PROCESS")"
  CURRENT_N="$(
    sed -n 's/.*--target-n \([0-9][0-9]*\).*/\1/p' \
      <<< "$PROCESS"
  )"

  CURRENT_DIR=""
  CURRENT_LOG=""
  CURRENT_SAMPLES=""
  CURRENT_CELL="none"
  if [[ -n "$ROOT" && -n "$CURRENT_N" ]]; then
    CURRENT_DIR="$ROOT/N$CURRENT_N"
    CURRENT_LOG="$CURRENT_DIR/stage4_n${CURRENT_N}_swap_enabled.run.log"
    CURRENT_SAMPLES="$CURRENT_DIR/stage4_n${CURRENT_N}_resource_samples.csv"
    [[ -f "$CURRENT_LOG" ]] &&
      CURRENT_CELL="$(
        grep '===== EXECUTE NOTEBOOK CELL' "$CURRENT_LOG" |
        tail -n1 |
        sed 's/.*CELL \([0-9][0-9]*\).*/\1/' ||
        true
      )"
  fi

  STATE="NOT_STARTED"
  NOTE="No overnight batch detected."
  if [[ -n "$PID" ]]; then
    STATE="RUNNING_N${CURRENT_N}"
    NOTE="The actual Python process is active."
  elif [[ -n "$ROOT" &&
          -f "$ROOT/stage4_overnight_batch_manifest.json" ]]; then
    BATCH_STATUS="$(
      python3 - "$ROOT/stage4_overnight_batch_manifest.json" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1]))["batch_status"])
PY
    )"
    if [[ "$BATCH_STATUS" == "PASS" ]]; then
      STATE="COMPLETED_PASS"
      NOTE="N121, N131, N141, and N151 completed."
    else
      STATE="$BATCH_STATUS"
      NOTE="The batch is between cases or stopped."
    fi
  fi

  clear 2>/dev/null || true
  line
  echo " SPINELLI STAGE 4 OVERNIGHT N121/N131/N141/N151 MONITOR"
  line
  printf ' Time:                 %s\n' "$(date -Is)"
  printf ' State:                %s\n' "$STATE"
  printf ' Interpretation:       %s\n' "$NOTE"
  printf ' Current N:            %s\n' "${CURRENT_N:-none}"
  printf ' Current cell:         %s\n' "${CURRENT_CELL:-none}"
  printf ' Batch root:           %s\n' "${ROOT:-not created}"
  printf ' Actual Python PID:    %s\n' "${PID:-not running}"
  printf ' Tmux:                 %s\n' \
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
  echo " CURRENT CASE RESOURCE PEAKS"
  subline
  if [[ -f "$CURRENT_SAMPLES" ]]; then
    awk -F, '
      NR > 1 {
        samples++
        if ($5+0 > rss) rss=$5+0
        if ($6+0 > swap) swap=$6+0
        if (($5+$6)+0 > combined) combined=($5+$6)+0
        if ($12+0 > system_swap) system_swap=$12+0
        if (first_in == "") first_in=$13+0
        if (first_out == "") first_out=$14+0
        last_in=$13+0
        last_out=$14+0
      }
      END {
        printf " Samples:              %d\n", samples
        printf " Max VmRSS:            %.2f GiB\n", rss/1048576
        printf " Max VmSwap:           %.2f GiB\n", swap/1048576
        printf " Max RSS+Swap:         %.2f GiB\n", combined/1048576
        printf " Max system swap:      %.2f GiB\n", system_swap/1048576
        printf " pswpin delta pages:   %.0f\n", last_in-first_in
        printf " pswpout delta pages:  %.0f\n", last_out-first_out
      }
    ' "$CURRENT_SAMPLES"
  else
    echo " No active resource samples."
  fi

  echo
  echo " COMPLETED CASES"
  subline
  if [[ -n "$ROOT" ]]; then
    for N in 121 131 141 151; do
      REPORT="$ROOT/N$N/stage4_n${N}_swap_enabled_report.txt"
      if [[ -f "$REPORT" ]] &&
         grep -q "^STAGE4_N${N}_SWAP_ENABLED_RUN_RESULT=PASS$" \
           "$REPORT"; then
        echo " N${N}: PASS"
      else
        echo " N${N}: pending"
      fi
    done
  else
    echo " Batch not created."
  fi

  echo
  echo " LAST BATCH LOG LINES"
  subline
  [[ -n "$ROOT" &&
     -f "$ROOT/stage4_overnight_batch.run.log" ]] &&
    tail -n36 "$ROOT/stage4_overnight_batch.run.log" ||
    echo " No batch log."
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
