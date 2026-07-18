# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-18  
**Expected repository baseline before publication:** `9d450e09789fb5187c433e74df0edcec1ad2295c`  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Completed

- Spatial sequence N61 through N111: PASS
- Proper-time validation: PASS
- Streaming-memory regression: PASS
- N111 corrected resource sampling: PASS
- Six-grid principal monotonicity: PASS

## N111 resources

- Peak RSS: 238.242134 GiB
- Peak process swap: 75.525066 GiB
- Peak RSS plus process swap: 310.656925 GiB
- Runtime: 1425.53 seconds

## Current phase

Publish N111 and run a guarded overnight batch:

`N121 → N131 → N141 → N151`

The workflow permits paging, samples the actual Python process, analyzes
the cumulative spatial sequence after every case, and stops on execution
failure or loss of principal monotonicity.

## Next decision

N151 is included conditionally and starts only after N141 passes and preserves monotonicity. A successful N151 ten-grid result recommends N161.
