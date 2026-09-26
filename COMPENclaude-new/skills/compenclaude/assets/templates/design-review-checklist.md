# Design Review Checklist

**Project:**
**Reviewer:**
**Date:** YYYY-MM-DD
**Target:** (FPGA part / MCU part number / simulator)
**Clock(s):**

## Interface

- [ ] Every port has a documented width, direction, and meaning
- [ ] Reset type stated (sync/async, active-high/low) and used consistently
- [ ] Clock domains listed; every crossing identified

## HDL

- [ ] Sequential logic uses `always_ff` with `<=`; combinational uses `always_comb` with `=`
- [ ] Every `always_comb` output has a default assignment (no latches in the synthesis report)
- [ ] Every `case` has a `default`
- [ ] No width mismatch warnings; constants sized
- [ ] Signed arithmetic is intentional (`signed` / `$signed`)
- [ ] No signal driven from two blocks; no combinational loops
- [ ] CDC: single bits through 2-FF synchronizers; buses through Gray code, handshake, or async FIFO
- [ ] Reset deasserts synchronously
- [ ] Timing constraints written; worst negative slack ≥ 0

## Firmware

- [ ] Peripheral clocks enabled before register access
- [ ] ISRs short, flags cleared, no blocking calls
- [ ] ISR-shared data `volatile` and accessed atomically
- [ ] Stack size checked (per task under an RTOS)
- [ ] Watchdog refreshed only when all tasks are healthy
- [ ] Pins in a safe state from reset until configured
- [ ] Error paths handled (timeouts on every wait loop)

## Verification

- [ ] Self-checking testbench, not waveform eyeballing
- [ ] Corner cases: reset mid-operation, back-to-back inputs, max/min values, overflow
- [ ] Tested on hardware at the target clock

## Findings

| # | Severity | Location | Issue | Fix |
|---|---|---|---|---|
| 1 | | | | |
