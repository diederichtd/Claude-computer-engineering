# Computer Engineering Formula Sheet

Keep only the sections your exam covers.

## Numbers

- n-bit unsigned: 0 … 2^n − 1. Two's complement: −2^(n−1) … 2^(n−1) − 1
- Negate: invert bits, add 1. Signed overflow: same-sign operands, different-sign result
- IEEE 754 single: 1 | 8 (bias 127) | 23. Double: 1 | 11 (bias 1023) | 52
- Value = (−1)^s × 1.f × 2^(e − bias)

## Logic and timing

- De Morgan: (AB)' = A' + B', (A + B)' = A'B'
- Setup: T_clk ≥ t_cq + t_pd + t_setup. Hold: t_cq + t_cd ≥ t_hold
- f_max = 1 / (t_cq + t_pd,max + t_setup)
- Dynamic power: P = α C V² f

## Performance

- CPU time = IC × CPI / f
- CPI = Σ (fraction_i × CPI_i)
- Amdahl: S = 1 / ((1 − p) + p/s)
- Pipeline CPI = 1 + stalls per instruction

## Caches

- offset = log2(block), sets = size / (block × ways), index = log2(sets), tag = A − index − offset
- AMAT = hit + miss rate × penalty (nest for multiple levels, local miss rates)

## Virtual memory

- offset = log2(page), VPN = VA − offset, flat table = 2^VPN × PTE size
- TLB reach = entries × page size
- EAT with faults = (1 − p) × t_mem + p × t_fault

## Operating systems

- Turnaround = completion − arrival. Waiting = turnaround − burst
- Deadlock needs: mutual exclusion, hold and wait, no preemption, circular wait
- RMS bound: Σ Ci/Ti ≤ n(2^(1/n) − 1)

## Networking

- Transmission = L/R. Propagation = d/s. BDP = R × RTT
- Hosts per subnet = 2^(32 − prefix) − 2
- Hamming parity bits: 2^r ≥ m + r + 1

## Embedded and circuits

- Timer period = prescaler × (reload + 1) / f_clk
- UART 8N1: bytes/s = baud / 10
- ADC LSB = Vref / 2^N
- τ = RC, f_c = 1/(2πRC), LED R = (Vs − Vf) / I
