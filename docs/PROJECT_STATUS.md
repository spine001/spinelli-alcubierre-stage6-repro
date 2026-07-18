# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-17  
**Expected repository baseline before this update:** `535de0e739eee30a370a3d9c3a5ac7230b07fdee`  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Completed

- N61/N71/N81/N91/N101 spatial sequence: PASS
- N71 proper-time matrix: PASS
- N81 proper-time confirmation: PASS
- Streaming-memory regressions: PASS
- N101 five-grid analysis: PASS
- N101 peak RSS: 225.275547 GiB
- N101 wall time: 620.23 seconds
- N101 swap: 0 GiB

## Current task

Publish N101 and execute N111 with swap enabled.

The N111 runner uses the same validated streaming numerical implementation.
Its notebook memory-budget selector is set to 512 GiB so that the requested
N111 grid is not reduced before execution.

## Resource policy

Swap and paging are accepted. They are measured rather than treated as
failures. The only hard execution failures are:

- invalid notebook or script integrity;
- a competing heavy calculation;
- insufficient virtual-memory or result-storage capacity;
- a nonzero process exit;
- a failed numerical run; or
- loss of the principal monotonic spatial trend.

## Next decision

A successful monotonic N111 run produces:

`PHASE7_RECOMMENDATION=BUILD_N121_SWAP_ENABLED_RUNNER`

The current rough N121 working-set projection is 464.056 GiB,
to be replaced by a projection from the measured N111 footprint.
