#!/usr/bin/env bash
set -u

TARGET="${1:-81}"
MODE="${2:-}"
case "$TARGET" in
  71|81) ;;
  *) echo "Usage: $0 71|81 [--watch]" >&2; exit 2 ;;
esac

REPO="${SPINELLI_REPO:-/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro}"
SESSION="spinelli-stage4-N${TARGET}"
LINK="$REPO/results/stage4_revalidation_N${TARGET}_latest"
REFRESH="${SPINELLI_MONITOR_REFRESH:-10}"

if [[ "$TARGET" == "71" ]]; then
  PY_PATTERN='run_stage4_n71_three_grid_analysis[.]py'
  WRAPPER_PATTERN='[b]ash .*run_scripts/run_stage4_n71_three_grid[.]sh'
  LOG_NAME='stage4_n71_three_grid.run.log'
  REPORT_NAME='stage4_n71_three_grid_report.txt'
  PREFLIGHT_GLOB='stage4_n71_three_grid_preflight_*.txt'
  PASS_MARKER='STAGE4_N71_RUN_RESULT=PASS'
else
  PY_PATTERN='run_stage4_n81_dense_convergence[.]py'
  WRAPPER_PATTERN='[b]ash .*run_scripts/run_stage4_n81_dense_convergence[.]sh'
  LOG_NAME='stage4_n81_dense_convergence.run.log'
  REPORT_NAME='stage4_n81_dense_convergence_report.txt'
  PREFLIGHT_GLOB='stage4_n81_dense_convergence_preflight_*.txt'
  PASS_MARKER='STAGE4_N81_RUN_RESULT=PASS'
fi

line() { printf '%*s\n' 96 '' | tr ' ' '='; }
subline() { printf '%*s\n' 96 '' | tr ' ' '-'; }

latest_preflight() {
  find "$REPO/reports" -maxdepth 1 -type f -name "$PREFLIGHT_GLOB" \
    -printf '%T@ %p\n' 2>/dev/null |
    sort -nr | head -n 1 | sed 's/^[^ ]* //'
}

snapshot() {
  local pid wrapper run_dir log report preflight state interpretation
  pid="$(pgrep -f "$PY_PATTERN" | head -n 1 || true)"
  wrapper="$(pgrep -f "$WRAPPER_PATTERN" | head -n 1 || true)"
  preflight="$(latest_preflight)"
  run_dir=""; log=""; report=""

  if [[ -L "$LINK" ]]; then
    run_dir="$(readlink -f "$LINK" 2>/dev/null || true)"
    [[ -n "$run_dir" ]] && log="$run_dir/$LOG_NAME"
    [[ -n "$run_dir" ]] && report="$run_dir/$REPORT_NAME"
  fi

  state="NOT_STARTED"
  interpretation="No run directory or active process detected."
  if [[ -n "$pid" ]]; then
    state="RUNNING"; interpretation="Python computation is active."
  elif [[ -f "$report" ]] && grep -q "^${PASS_MARKER}$" "$report"; then
    state="COMPLETED_PASS"; interpretation="Final report contains the PASS marker."
  elif [[ -f "$log" ]] && grep -q '^RUN_EXIT_CODE=[1-9][0-9]*$' "$log"; then
    state="FAILED"; interpretation="The wrapper recorded a nonzero exit code."
  elif [[ -n "$wrapper" ]]; then
    state="WRAPPER_ACTIVE"; interpretation="Wrapper active; Python may be starting or finalizing."
  elif [[ -n "$run_dir" ]]; then
    state="STOPPED_OR_FINISHED"; interpretation="Run directory exists but no active Python process."
  elif tmux has-session -t "$SESSION" 2>/dev/null; then
    state="TMUX_EXISTS_NO_RUN"; interpretation="Tmux exists, but no run directory was created."
  fi

  clear 2>/dev/null || true
  line
  printf ' SPINELLI STAGE 4 N%s MONITOR\n' "$TARGET"
  line
  printf ' Time:              %s\n' "$(date -Is)"
  printf ' State:             %s\n' "$state"
  printf ' Interpretation:    %s\n' "$interpretation"
  printf ' Tmux:              %s\n' "$(tmux has-session -t "$SESSION" 2>/dev/null && echo PRESENT || echo ABSENT)"
  printf ' Symlink:           %s\n' "$([[ -L "$LINK" ]] && echo PRESENT || echo ABSENT)"
  printf ' Run directory:     %s\n' "${run_dir:-not created}"
  printf ' Python PID:        %s\n' "${pid:-not running}"
  printf ' Wrapper PID:       %s\n' "${wrapper:-not running}"
  line

  printf ' SYSTEM MEMORY\n'; subline
  free -h
  awk '
    /MemAvailable:/ {ma=$2}
    /SwapTotal:/ {st=$2}
    /SwapFree:/ {sf=$2}
    END {
      printf " MemAvailable: %.2f GiB\n", ma/1048576;
      printf " Swap used:    %.2f GiB of %.2f GiB\n", (st-sf)/1048576, st/1048576;
    }' /proc/meminfo

  if [[ -n "$pid" && -r "/proc/$pid/status" ]]; then
    printf '\n N%s PROCESS\n' "$TARGET"; subline
    ps -p "$pid" -o pid,ppid,state,etime,%cpu,%mem,rss,vsz,cmd --no-headers || true
    awk '
      /^VmRSS:/ {rss=$2}
      /^VmSwap:/ {swap=$2}
      /^Threads:/ {threads=$2}
      END {
        printf " VmRSS:   %.2f GiB\n", rss/1048576;
        printf " VmSwap:  %.2f GiB\n", swap/1048576;
        printf " Threads: %s\n", threads;
      }' "/proc/$pid/status"
  fi

  printf '\n RECENT PAGING\n'; subline
  command -v vmstat >/dev/null 2>&1 && vmstat 1 2 | tail -n 3 || echo "vmstat unavailable"

  printf '\n LATEST PREFLIGHT\n'; subline
  if [[ -f "$preflight" ]]; then
    echo " $preflight"; tail -n 18 "$preflight"
  else
    echo " No preflight report."
  fi

  printf '\n LAST LOG LINES\n'; subline
  if [[ -f "$log" ]]; then
    echo " $log"; tail -n 28 "$log"
  else
    echo " No run log."
  fi

  printf '\n TMUX PANE TAIL\n'; subline
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux capture-pane -pt "$SESSION":0 -S -24 2>/dev/null | tail -n 24
  else
    echo " Tmux session absent."
  fi
  line
}

if [[ "$MODE" == "--watch" ]]; then
  while true; do snapshot; sleep "$REFRESH"; done
elif [[ -z "$MODE" ]]; then
  snapshot
else
  echo "Usage: $0 71|81 [--watch]" >&2
  exit 2
fi
