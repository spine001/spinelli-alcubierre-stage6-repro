from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import re
import json

REPO = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro")
LATEST = REPO / "results" / "stage6C_alcubierre_highres_latest"

CASES = []
for N in [181, 201, 221]:
    for VS in ["0p5", "1"]:
        CASES.append((N, VS, f"N{N}_v{VS}_sigma4_R3"))

PHASES = [
    ("fit pass tile", 0.35),
    ("score pass tile", 0.75),
    ("Finished", 1.00),
]

def read(path):
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""

def proc_lines():
    try:
        out = subprocess.check_output(
            ["pgrep", "-af", "spinelli_stage6b_tiled_cli.py|run_stage6C_alcubierre"],
            text=True
        )
        return [x for x in out.splitlines() if x.strip()]
    except subprocess.CalledProcessError:
        return []

def memory_text():
    try:
        free = subprocess.check_output(["free", "-h"], text=True).splitlines()
        swap = subprocess.check_output(["swapon", "--show"], text=True).splitlines()
        disk = subprocess.check_output(["df", "-h", "/"], text=True).splitlines()[-1]
        mem_line = free[1].strip() if len(free) > 1 else "-"
        swap_line = free[2].strip() if len(free) > 2 else "-"
        swap_detail = " | ".join(x.strip() for x in swap[1:]) if len(swap) > 1 else "no swap detail"
        return mem_line, swap_line, swap_detail, disk
    except Exception as e:
        return "-", "-", str(e), "-"

def top_memory():
    try:
        return subprocess.check_output(
            "ps -eo pid,comm,rss,vsz,%mem,%cpu --sort=-rss | head -8",
            shell=True, text=True
        ).strip()
    except Exception as e:
        return str(e)

def parse_progress(log_text):
    total_tiles = None
    m = re.search(r":\s+([0-9]+)\s+tiles", log_text)
    if m:
        total_tiles = int(m.group(1))

    fit = [int(x) for x in re.findall(r"fit pass tile\s+([0-9]+)/([0-9]+)", log_text)]
    score = [int(x) for x in re.findall(r"score pass tile\s+([0-9]+)/([0-9]+)", log_text)]

    if score:
        last = score[-1]
        total = int(re.findall(r"score pass tile\s+[0-9]+/([0-9]+)", log_text)[-1])
        return "score pass", 0.50 + 0.50 * last / max(total, 1), f"{last:,}/{total:,}"

    if fit:
        last = fit[-1]
        total = int(re.findall(r"fit pass tile\s+[0-9]+/([0-9]+)", log_text)[-1])
        return "fit pass", 0.50 * last / max(total, 1), f"{last:,}/{total:,}"

    if "Stage 6B case" in log_text:
        return "started", 0.02, "-"

    return "-", 0.0, "-"

def status_for(label, qtxt, runbase):
    case_dir = runbase / label
    summary = case_dir / "case_summary.csv"

    if summary.exists():
        return ["DONE", "finished", 1.0, "done", "finished"]

    log = runbase / f"{label}.run.log"
    txt = read(log)

    if "FAILED " + label in qtxt or "Traceback" in txt or "FAILED" in txt:
        return ["ERROR", "failed", 0.0, "-", last_line(txt)]

    if txt:
        phase, pct, tiles = parse_progress(txt)
        return ["RUN", phase, pct, tiles, last_line(txt)]

    return ["NEXT", "-", 0.0, "-", "-"]

def last_line(txt):
    lines = [x.strip() for x in txt.splitlines() if x.strip()]
    return lines[-1][-100:] if lines else "-"

def main():
    now = datetime.now()

    if not LATEST.exists():
        print()
        print("Stage 6C monitor")
        print("=" * 100)
        print("No latest Stage 6C run found yet.")
        print("Expected:", LATEST)
        print()
        return

    runbase = LATEST.resolve()
    qtxt = read(runbase / "stage6C_alcubierre_highres_queue.log")
    procs = proc_lines()
    mem, swap, swap_detail, disk = memory_text()

    rows = []
    units = 0.0
    for N, VS, label in CASES:
        s = status_for(label, qtxt, runbase)
        units += s[2]
        rows.append((N, VS, label, *s))

    overall = 100.0 * units / len(CASES)

    print()
    print("Stage 6C Alcubierre high-resolution monitor")
    print("=" * 120)
    print(f"Now: {now.strftime('%a %b %d %I:%M:%S %p')}    Process: {'RUNNING' if procs else 'NOT RUNNING'}")
    print(f"Run base: {runbase}")
    print(f"Overall: {overall:5.1f}%")
    print("=" * 120)
    print(f"{'N':<6} {'v_s':<6} {'Status':<8} {'Phase':<14} {'Case %':>8} {'Tiles':<18} {'Last line'}")
    print("-" * 120)

    for N, VS, label, status, phase, pct, tiles, last in rows:
        print(f"{N:<6} {VS:<6} {status:<8} {phase:<14} {100*pct:>7.1f}% {tiles:<18} {last}")

    print("=" * 120)
    print("Memory:")
    print(mem)
    print(swap)
    print("Swap detail:", swap_detail)
    print("Disk /:", disk)
    print("=" * 120)
    print("Top memory processes:")
    print(top_memory())
    print("=" * 120)
    print("Active:")
    if procs:
        for p in procs[:8]:
            print(p[-115:])
    else:
        print("No active Stage 6C solver process found.")
    print()

if __name__ == "__main__":
    main()
