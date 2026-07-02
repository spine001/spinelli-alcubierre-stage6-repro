#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import subprocess
import re

REPO = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro")
LATEST = REPO / "results" / "stage6D_alcubierre_highres_latest"

CASE_SPECS = [
    (241, "0.5"),
    (241, "1.0"),
    (261, "0.5"),
    (261, "1.0"),
    (301, "0.5"),
    (301, "1.0"),
]


def case_label(N, vs):
    if vs == "0.5":
        return f"N{N}_v0p5_sigma4_R3"
    if vs in ("1.0", "1"):
        return f"N{N}_v1_sigma4_R3"
    return f"N{N}_v{vs.replace('.', 'p')}_sigma4_R3"


def read(path):
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""


def proc_lines():
    try:
        out = subprocess.check_output(
            ["pgrep", "-af", "spinelli_stage6b_tiled_cli.py|run_stage6D_alcubierre_highres"],
            text=True,
        )
        lines = [x for x in out.splitlines() if x.strip()]
        return [x for x in lines if "stage6D_eta.py" not in x]
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
            "ps -eo pid,stat,comm,rss,vsz,%mem,%cpu,wchan:24 --sort=-rss | head -8",
            shell=True,
            text=True,
        ).strip()
    except Exception as e:
        return str(e)


def last_line(txt):
    lines = [x.strip() for x in txt.splitlines() if x.strip()]
    return lines[-1][-110:] if lines else "-"


def parse_progress(log_text):
    score_matches = re.findall(r"score pass tile\s+([0-9]+)/([0-9]+)", log_text)
    if score_matches:
        last_s, total_s = score_matches[-1]
        last = int(last_s)
        total = int(total_s)
        pct = 0.50 + 0.50 * last / max(total, 1)
        return "score pass", pct, f"{last:,}/{total:,}"

    fit_matches = re.findall(r"fit pass tile\s+([0-9]+)/([0-9]+)", log_text)
    if fit_matches:
        last_s, total_s = fit_matches[-1]
        last = int(last_s)
        total = int(total_s)
        pct = 0.50 * last / max(total, 1)
        return "fit pass", pct, f"{last:,}/{total:,}"

    if "Finished " in log_text:
        return "finished", 1.0, "done"

    if "Stage 6B case" in log_text:
        return "started", 0.02, "-"

    return "-", 0.0, "-"


def status_for(runbase, qtxt, N, vs):
    label = case_label(N, vs)
    summary = runbase / label / "case_summary.csv"

    if summary.exists():
        return ["DONE", "finished", 1.0, "done", "finished"]

    log = runbase / f"{label}.run.log"
    txt = read(log)

    if ("FAILED " + label) in qtxt or "Traceback" in txt or "FAILED" in txt:
        return ["ERROR", "failed", 0.0, "-", last_line(txt)]

    if txt:
        phase, pct, tiles = parse_progress(txt)
        return ["RUN", phase, pct, tiles, last_line(txt)]

    return ["NEXT", "-", 0.0, "-", "-"]


def main():
    now = datetime.now()

    print()
    print("Stage 6D Alcubierre higher-resolution monitor")
    print("=" * 120)

    if not LATEST.exists():
        print("No latest Stage 6D run found yet.")
        print("Expected:", LATEST)
        print("=" * 120)
        return

    runbase = LATEST.resolve()
    qtxt = read(runbase / "stage6D_alcubierre_highres_queue.log")
    procs = proc_lines()
    mem, swap, swap_detail, disk = memory_text()

    rows = []
    units = 0.0

    for N, vs in CASE_SPECS:
        s = status_for(runbase, qtxt, N, vs)
        units += s[2]
        rows.append((N, vs, *s))

    overall = 100.0 * units / len(CASE_SPECS)

    print(f"Now: {now.strftime('%a %b %d %I:%M:%S %p')}    Process: {'RUNNING' if procs else 'NOT RUNNING'}")
    print(f"Run base: {runbase}")
    print(f"Overall full 6-case ladder: {overall:5.1f}%")
    print("=" * 120)
    print(f"{'N':<6} {'v_s':<6} {'Status':<8} {'Phase':<14} {'Case %':>8} {'Tiles':<18} {'Last line'}")
    print("-" * 120)

    for N, vs, status, phase, pct, tiles, last in rows:
        print(f"{N:<6} {vs:<6} {status:<8} {phase:<14} {100*pct:>7.1f}% {tiles:<18} {last}")

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
        print("No active Stage 6D solver process found.")
    print()


if __name__ == "__main__":
    main()
