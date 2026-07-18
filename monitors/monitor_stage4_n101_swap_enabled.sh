#!/usr/bin/env bash
set -u
REPO="${SPINELLI_REPO:-/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro}"
SESSION="${SPINELLI_N101_TMUX:-spinelli-stage4-N101}"
LINK="$REPO/results/stage4_revalidation_N101_swap_enabled_latest"
REFRESH="${SPINELLI_MONITOR_REFRESH:-10}"
line(){ printf '%*s\n' 100 ''|tr ' ' '='; }
sub(){ printf '%*s\n' 100 ''|tr ' ' '-'; }
pid(){ ps -eo pid=,comm=,args=|awk '$2~/^python/&&index($0,"run_stage4_n101_optimized_swap_enabled.py"){print $1;exit}'; }
snapshot(){
 P="$(pid)"; OUT=""; LOG=""; REPORT=""; SAMPLES=""
 [[ -L "$LINK" ]] && OUT="$(readlink -f "$LINK" 2>/dev/null||true)"
 [[ -n "$OUT" ]] && LOG="$OUT/stage4_n101_optimized_swap_enabled.run.log"
 [[ -n "$OUT" ]] && REPORT="$OUT/stage4_n101_five_grid_report.txt"
 [[ -n "$OUT" ]] && SAMPLES="$OUT/stage4_n101_resource_samples.csv"
 STATE="NOT_STARTED"; NOTE="No N101 run detected."
 if [[ -n "$P" ]]; then STATE="RUNNING"; NOTE="Python active; paging is allowed."
 elif [[ -f "$REPORT" ]] && grep -q '^STAGE4_N101_FIVE_GRID_ANALYSIS_RESULT=PASS$' "$REPORT"; then STATE="COMPLETED_PASS"; NOTE="N101 and five-grid analysis completed."
 elif [[ -n "$OUT" ]]; then STATE="STOPPED_OR_FAILED"; NOTE="Output exists without active Python or final PASS."; fi
 clear 2>/dev/null||true
 line; echo " SPINELLI STAGE 4 N101 SWAP-ENABLED MONITOR"; line
 printf ' Time:             %s\n' "$(date -Is)"
 printf ' State:            %s\n' "$STATE"
 printf ' Interpretation:   %s\n' "$NOTE"
 printf ' Output:           %s\n' "${OUT:-not created}"
 printf ' Python PID:       %s\n' "${P:-not running}"
 line
 echo " SYSTEM MEMORY"; sub; free -h
 awk '/MemAvailable:/{m=$2}/SwapTotal:/{t=$2}/SwapFree:/{f=$2}END{printf " MemAvailable: %.2f GiB\n Swap used: %.2f GiB of %.2f GiB\n",m/1048576,(t-f)/1048576,t/1048576}' /proc/meminfo
 if [[ -n "$P" && -r "/proc/$P/status" ]]; then
   echo; echo " ACTIVE PYTHON"; sub
   ps -p "$P" -o pid,ppid,comm,state,etime,%cpu,%mem,rss,vsz,args
   awk '/^VmRSS:/{r=$2}/^VmSwap:/{s=$2}/^Threads:/{t=$2}END{printf " VmRSS: %.2f GiB\n VmSwap: %.2f GiB\n Threads: %s\n",r/1048576,s/1048576,t}' "/proc/$P/status"
 fi
 echo; echo " PAGING"; sub; vmstat 1 2|tail -n3
 echo; echo " RESOURCE SAMPLE PEAKS"; sub
 if [[ -f "$SAMPLES" ]]; then
   awk -F, 'NR>1{if($4>r)r=$4;if($5>s)s=$5;if(min==0||$6<min)min=$6;if($7>ss)ss=$7}END{printf " Max VmRSS: %.2f GiB\n Max VmSwap: %.2f GiB\n Min MemAvailable: %.2f GiB\n Max system swap used: %.2f GiB\n",r/1048576,s/1048576,min/1048576,ss/1048576}' "$SAMPLES"
 else echo " No samples yet."; fi
 echo; echo " LAST LOG LINES"; sub; [[ -f "$LOG" ]] && tail -n32 "$LOG" || echo " No log."
 line
}
case "${1:-}" in --watch) while true;do snapshot;sleep "$REFRESH";done;; "") snapshot;; *) echo "Usage: $0 [--watch]" >&2;exit 2;; esac
