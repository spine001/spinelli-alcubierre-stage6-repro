# Stage 4R N191 Final Acceptance and N201 Host-Resource Boundary

**Closure date:** 2026-07-28
**Audited repository baseline:** `42262b77b959ca390e67f4834484d959bf99b979`
**Production notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Scientific disposition

The dense Stage 4R resolution campaign is complete and accepted at N191.
N191 production passed, the cumulative 14-grid analysis passed, and all four
principal diagnostics are strictly decreasing from N61 through N191.

N201 is not a scientific failure and is not an accepted grid. It is an
incomplete host-resource event: the machine crashed before a complete
production report and cumulative acceptance analysis could be produced.
Partial N201 diagnostic values must not be appended to the accepted
convergence sequence.

The result markers are:

```text
STAGE4_FINAL_ACCEPTED_GRID=N191
STAGE4_N201_DISPOSITION=ABORTED_HOST_CRASH
STAGE4_RESOLUTION_CAMPAIGN_RESULT=PASS_AT_N191
N201_RESTART_STATUS=PROHIBITED_BY_USER_DECISION
```

The incomplete run discussed here is the dense Stage 4R N201 attempt. The
previously completed tiled Stage 6C N201 calculation is a different workflow
and remains valid.

## Accepted 14-grid sequence

| N | Relative Bianchi | Peak-relative rho error | Hessian-Q normalized | HTR normalized |
|---:|---:|---:|---:|---:|
| 61 | `6.031912101890444e-3` | `4.964638263844123e-2` | `1.8923608329206223e-2` | `1.661441080787198e-2` |
| 71 | `4.538437626932157e-3` | `3.7033850908382716e-2` | `1.5545047560557315e-2` | `1.2705486513730447e-2` |
| 81 | `3.5299983833249567e-3` | `2.858669536805789e-2` | `1.357449810639878e-2` | `1.0241875755526996e-2` |
| 91 | `2.819880281060446e-3` | `2.2740302310159808e-2` | `1.240857338767482e-2` | `8.660663765603933e-3` |
| 101 | `2.302252148004587e-3` | `1.8509149568745848e-2` | `1.170914984708746e-2` | `7.637756312486901e-3` |
| 111 | `1.9139352284350659e-3` | `1.5352091640846053e-2` | `1.128348028902871e-2` | `6.974356346946944e-3` |
| 121 | `1.6154968442510104e-3` | `1.293262207483022e-2` | `1.1020782204151045e-2` | `6.543942971459145e-3` |
| 131 | `1.381367736108725e-3` | `1.1042409601585942e-2` | `1.0856747770075727e-2` | `6.264808638118429e-3` |
| 141 | `1.1944140352331712e-3` | `9.537596769751532e-3` | `1.0753517256412144e-2` | `6.084069052097357e-3` |
| 151 | `1.0428224711343365e-3` | `8.319712174904223e-3` | `1.0688413940932909e-2` | `5.967536479538136e-3` |
| 161 | `9.18242956584871e-4` | `7.320097473500955e-3` | `1.064759908918181e-2` | `5.89310323169368e-3` |
| 171 | `8.146427863586094e-4` | `6.489901446406724e-3` | `1.0622467851274582e-2` | `5.846426314144421e-3` |
| 181 | `7.275783006429609e-4` | `5.793506003873614e-3` | `1.0607573463386054e-2` | `5.818144864296481e-3` |
| 191 | `6.537193948997797e-4` | `5.203111797498817e-3` | `1.059941113117432e-2` | `5.802102531478413e-3` |

The accepted report gives descriptive log-log slopes of
`1.934719968` for relative Bianchi and `1.961269788` for the
peak-relative rho error. The acceptance claim rests on the reported gate
results and strict principal monotonicity, not on extrapolation beyond N191.

## N171 anomaly and canonical repair

The historical N171 Stage 4A rho result was
`0.09066275784751161`, compared with
`0.007320097473500955` at N161. This approximately 12.4-fold jump was
inconsistent with the convergent sequence.

An independent N161/N171 V3 diagnostic reused the valid N161 V2 result and
freshly recomputed N171. It obtained:

- fresh N171 rho error: `0.006489901446406724`;
- N171/N161 ratio: `0.88658675241694895`;
- fresh/historical N171 ratio: `0.071582881444245086`.

The historical outlier was not reproduced. The canonical repair copied the
historical N171 directory, preserved the original artifacts under
`provenance/historical_original`, replaced only Stage 4A, retained Stages
4B/4C/4D, and reran the cumulative gate. The repaired N171 point passed.

Relevant package hashes:

| Evidence | SHA-256 |
|---|---|
| N161/N171 V3 diagnostic archive | `c09cede0163b30b29c4d23ec568ea33e9b108c76dc2057731f84c330fae83a06` |
| N171 canonical-repair package | `728b62635eff9342ae1f95111fc93f8afe6fd08c76862457e7b2cb9a3c0f1345` |

## N191 accepted values

| Quantity | Value |
|---|---:|
| Relative Bianchi residual | `0.00065371939489977974` |
| Peak-relative rho error | `0.0052031117974988168` |
| Hessian-Q normalized residual | `0.010599411131174319` |
| HTR normalized residual | `0.0058021025314784133` |
| Fitted lambda | `0.016759636831295006` |
| Fitted beta | `-1.0419365581915676` |
| Action/fit ratio | `1.0012282548650826` |
| Tensor difference | `0.032588928990303821%` |
| Action penalty | `0.12282548650826008%` |
| HTR improvement | `0.43983721678171295` |

N191 used `Δτ=0.04`. Peak RSS was `239.722076416 GiB`,
peak process swap was `2329.430241 GiB`, sampled RSS plus process swap was
`2552.897030 GiB`, peak system swap was `2330.477257 GiB`, and runtime was
`261480 s` (`72.633 h`).

N191 evidence hashes:

| Evidence | SHA-256 |
|---|---|
| Production report | `298f4feb66f2146090dbb2d756bf0d9958b391ebd8bc5c97ac179e63e3e937a7` |
| 14-grid analysis report | `ca0480df46c1406f208548ec60e8738d16b2dd748ea27d96a90a4d1c4521431e` |

## N201 host-resource forensics

The N201 resource log contains 19,646 valid samples at a median 5-second
cadence over `99003 s` (`27.500833 h`). The terminal record shows:

| Quantity | Value |
|---|---:|
| Peak RSS | `239.795516968 GiB` |
| Peak process swap | `2759.650142670 GiB` |
| Peak system swap | `2760.633049011 GiB` |
| Maximum sampled RSS + process swap | `2982.605003357 GiB` |
| Final available RAM | `0.358764648 GiB` |
| Final process state | `D` |
| Increase in major faults | `511743168` |

The partial run recorded intermediate Bianchi, Hessian-Q, lambda, and beta
values, but it did not produce a complete rho diagnostic, HTR diagnostic,
action comparison, production PASS, or cumulative PASS. Those intermediate
values are computational diagnostics only.

N201 forensic hashes:

| Evidence | SHA-256 |
|---|---|
| Forensic report | `03e7f34ded947ec019be9560b9f85a8b4f7e829d49a5e446cf0616fbd99e3b13` |
| Resource CSV | `9065a88b816e1d11734f3e31f8693e20cb41216ca2d576d497000d4b5beacc3d` |
| Partial run log | `8c5ce5d8297c86f4e61fe91ff3af723caa29b6ebc6e4a648bfc076ab9dd83d36` |

## Terminal archive

The recovery archive is:

```text
results/stage4_resume_N181_N201_20260721_140641_STOP_AT_N191_SERVER_CRASH_20260727_133529.zip
```

SHA-256:

```text
ba4206a21a88d9db088059a1f220d2371ee0e2ee7f63b81b848b7f1db4f73809
```

It preserves accepted N181/N191 outputs, the partial N201 resource record,
the continuation manifest, and the explicit stop marker. It is evidence of
the terminal campaign state; it is not authorization to resume N201.
