# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-28
**Repository baseline audited:** `42262b77b959ca390e67f4834484d959bf99b979`
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Stage 4R resolution campaign

- `STAGE4_FINAL_ACCEPTED_GRID=N191`
- `STAGE4_N201_DISPOSITION=ABORTED_HOST_CRASH`
- `STAGE4_RESOLUTION_CAMPAIGN_RESULT=PASS_AT_N191`
- `N201_RESTART_STATUS=PROHIBITED_BY_USER_DECISION`

Dense Stage 4R is accepted through N191. The 14-grid principal-diagnostic
sequence from N61 through N191 is strictly decreasing. N191 production and
the cumulative 14-grid analysis both report PASS.

N201 did not complete. The host was under terminal memory pressure, the
process was in uninterruptible sleep, and no complete N201 production report
or cumulative acceptance report exists. The partial N201 output is retained
only as computational-forensic evidence and is excluded from scientific
convergence claims.

This disposition applies to the incomplete **dense Stage 4R N201** attempt.
It does not alter the previously completed **tiled Stage 6C N201** result.

## Accepted N191 result

| Quantity | N191 value |
|---|---:|
| Relative Bianchi residual | `6.5371939489977974e-4` |
| Peak-relative rho error | `5.2031117974988168e-3` |
| Hessian-Q normalized residual | `1.0599411131174319e-2` |
| HTR normalized residual | `5.8021025314784133e-3` |
| Fitted lambda | `1.6759636831295006e-2` |
| Fitted beta | `-1.0419365581915676` |
| Action/fit ratio | `1.0012282548650826` |
| Tensor difference | `0.032588928990303821%` |
| Action penalty | `0.12282548650826008%` |
| HTR improvement | `0.43983721678171295` |

## High-resolution resource record

| Grid | Peak RSS (GiB) | Peak process swap (GiB) | Peak RSS + swap (GiB) | Runtime (h) | Disposition |
|---:|---:|---:|---:|---:|---|
| N171 | 239.626575 | 1365.087284 | 1595.887947 | 22.428 | PASS after provenance-preserving Stage 4A repair |
| N181 | 239.712509 | 1795.056686 | 2023.914261 | 38.511 | PASS |
| N191 | 239.722076 | 2329.430241 | 2552.897030 | 72.633 | PASS; terminal accepted grid |
| N201 | 239.795517 | 2759.650143 | 2982.605003 | 27.501 sampled | Incomplete host-resource event |

## Publication state

The integrated self-contained HTML has been updated with:

- the terminal N191 result and 14-grid convergence evidence;
- the N171 anomaly diagnosis and provenance-preserving repair;
- N181/N191 resource scaling;
- N201 host-resource forensics and the no-restart disposition;
- explicit separation of dense Stage 4R N201 from tiled Stage 6C N201;
- repaired duplicated sections, internal anchor, and corrupted mathematical
  characters;
- embedded MathJax and embedded figure assets for offline use.

The historical Stage 4 authorization appendix remains in the article as an
audit record. Appendix AC is the terminal closure record.

## Next scientific boundary

No further dense Stage 4R resolution run is authorized. Any future extension
above N191 requires a new method or resource model and a new explicit
authorization; it is not a continuation of the closed N141–N201 campaign.
