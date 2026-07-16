#!/usr/bin/env bash
set -u
TARGET="${1:-71}"
MODE="${2:-}"
case "$TARGET" in 71|81) ;; *) echo "Usage: $0 71|81 [--watch]" >&2; exit 2;; esac
REPO="${SPINELLI_REPO:-/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro}"
SESSION="spinelli-stage4-N${TARGET}"
LINK="$REPO/results/stage4_revalidation_N${TARGET}_latest"
REFRESH="${SPINELLI_MONITOR_REFRESH:-10}"

if [[ "$TARGET" == 71 ]]; then
 PY_SCRIPT='run_stage4_n71_three_grid_analysis.py'
 WRAPPER='run_stage4_n71_three_grid.sh'
 LOG_NAME='stage4_n71_three_grid.run.log'
 REPORT_NAME='stage4_n71_three_grid_report.txt'
 PASS='STAGE4_N71_RUN_RESULT=PASS'
else
 PY_SCRIPT='run_stage4_n81_dense_convergence.py'
 WRAPPER='run_stage4_n81_dense_convergence.sh'
 LOG_NAME='stage4_n81_dense_convergence.run.log'
 REPORT_NAME='stage4_n81_dense_convergence_report.txt'
 PASS='STAGE4_N81_RUN_RESULT=PASS'
fi

find_python_pid() {
 ps -eo pid=,comm=,args= |
 awk -v script="$PY_SCRIPT" '
   $2 ~ /^python/ && index($0,script) {print $1; exit}
 '
}
find_wrapper_pid() {
 ps -eo pid=,comm=,args= |
 awk -v script="$WRAPPER" '
   $2 == "bash" && index($0,script) {print $1; exit}
 '
}
line(){ printf '%*s\n' 96 ''|tr ' ' '='; }
subline(){ printf '%*s\n' 96 ''|tr ' ' '-'; }

snapshot(){
 pid="$(find_python_pid)"; wrapper="$(find_wrapper_pid)"
 run_dir=""; log=""; report=""
 if [[ -L "$LINK" ]]; then
   run_dir="$(readlink -f "$LINK" 2>/dev/null||true)"
   [[ -n "$run_dir" ]] && log="$run_dir/$LOG_NAME" && report="$run_dir/$REPORT_NAME"
 fi
 state="NOT_STARTED"; interp="No run detected."
 if [[ -n "$pid" ]]; then state="RUNNING"; interp="Actual Python computation is active."
 elif [[ -f "$report" ]] && grep -q "^${PASS}$" "$report"; then state="COMPLETED_PASS"; interp="Final PASS marker present."
 elif [[ -f "$log" ]] && grep -q '^RUN_EXIT_CODE=[1-9][0-9]*$' "$log"; then state="FAILED"; interp="Nonzero exit recorded."
 elif [[ -n "$wrapper" ]]; then state="WRAPPER_ACTIVE"; interp="Wrapper active."
 elif [[ -n "$run_dir" ]]; then state="STOPPED_OR_FINISHED"; interp="Run directory exists, Python absent."
 elif tmux has-session -t "$SESSION" 2>/dev/null; then state="TMUX_EXISTS_NO_RUN"; interp="Tmux exists without a run."
 fi
 clear 2>/dev/null||true
 line; echo " SPINELLI STAGE 4 N${TARGET} MONITOR"; line
 printf ' Time:              %s\n' "$(date -Is)"
 printf ' State:             %s\n' "$state"
 printf ' Interpretation:    %s\n' "$interp"
 printf ' Run directory:     %s\n' "${run_dir:-not created}"
 printf ' Python PID:        %s\n' "${pid:-not running}"
 printf ' Wrapper PID:       %s\n' "${wrapper:-not running}"
 line
 echo " SYSTEM MEMORY"; subline; free -h
 if [[ -n "$pid" && -r "/proc/$pid/status" ]]; then
   echo; echo " PYTHON PROCESS"; subline
   ps -p "$pid" -o pid,ppid,comm,state,etime,%cpu,%mem,rss,vsz,args
   awk '/^VmRSS:/{r=$2}/^VmSwap:/{s=$2}/^Threads:/{t=$2}
        END{printf " VmRSS: %.2f GiB\n VmSwap: %.2f GiB\n Threads: %s\n",r/1048576,s/1048576,t}' "/proc/$pid/status"
 fi
 echo; echo " RECENT PAGING"; subline
 command -v vmstat >/dev/null 2>&1 && vmstat 1 2|tail -n3 || true
 echo; echo " LAST LOG LINES"; subline
 [[ -f "$log" ]] && tail -n28 "$log" || echo " No run log."
 echo; echo " TMUX PANE"; subline
 tmux has-session -t "$SESSION" 2>/dev/null && tmux capture-pane -pt "$SESSION":0 -S -20|tail -n20 || echo " Tmux absent."
 line
}
if [[ "$MODE" == "--watch" ]]; then while true; do snapshot; sleep "$REFRESH"; done
elif [[ -z "$MODE" ]]; then snapshot
else echo "Usage: $0 71|81 [--watch]" >&2; exit 2
fi
