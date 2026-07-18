# Stage 4 Overnight N121/N131/N141/N151 Batch Plan

**Date:** 2026-07-18  
**Execution policy:** swap allowed and measured  
**Notebook selector budget:** 1024 GiB

## Cases

| Case | Projected working set | CPU-only estimate | Planning range |
|---|---:|---:|---:|
| N121 | 438.7 GiB | 21.3 min | 33.5–45.3 min |
| N131 | 602.7 GiB | 29.3 min | 46.1–72.9 min |
| N141 | 808.8 GiB | 39.3 min | 61.9–107.6 min |
| N151 | 1063.9 GiB | 51.6 min | 81.4–150.6 min |

The combined planning range is approximately
3.7–6.3 hours.
These are planning estimates rather than deadlines; deeper paging can
extend the run.

## Sequential gates

The workflow runs:

`N121 → N131 → N141 → N151`

After every case it verifies process exit, notebook-cell PASS status,
historical-notebook integrity, canonical exports, actual-Python resource
sampling, and strict monotonic decrease of all principal diagnostics.

Any failed gate stops the batch before the next resolution.

## Why N151 is included

The projected N151 working set is approximately
1063.9 GiB, below the available physical-plus-swap
capacity. It is severe enough to use overnight processing time while
remaining well below the configured 3 TiB swap capacity.

## Outputs

Each case receives a separate directory and ZIP. The batch also creates
one aggregate ZIP and a final ten-grid N61-through-N151 report.

A successful N151 result is expected to recommend:

`BUILD_N161_SWAP_ENABLED_RUNNER`
