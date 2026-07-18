# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-18  
**Expected repository baseline:** `ff9f9c1435d9fbcbe26ce6ba2984a5ff17b947b5`  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Completed and reusable

- N121 production: PASS
- N121 seven-grid analysis: PASS
- N131 production: PASS
- N131 eight-grid analysis: PASS
- Principal sequence through N131: strictly monotonic
- N141 failed attempt: closed as selector-cap configuration failure

N121 and N131 are published and reused without recomputation.

## Current authorized continuation

`N141 → N151 → N161 → N171 → N181 → N191 → N201`

The sequence is conditional. Every completed case must pass and preserve
principal monotonicity before the next case starts.

## Resource policy

- Paging is allowed.
- Process swap is authorized up to 2990 GiB.
- N201 is the maximum authorized ladder point.
- N211 is excluded by the measured N131 N⁴ footprint projection.
- Physical RAM is not a hard resolution gate.
- Every failure or policy stop produces an aggregate recovery ZIP.

## Publication

This phase updates the integrated HTML, project status, N121/N131 evidence,
continuation runner, monitor, preflight, and cumulative spatial analysis.
The supplied installer performs an exact-path commit and optional push.
