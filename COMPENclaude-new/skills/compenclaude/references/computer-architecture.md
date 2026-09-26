# Computer architecture

Performance math, ISAs, pipelines, caches, virtual memory, and multicore, with the formulas and stall rules exam problems depend on.

## Contents

- Performance
- ISA basics
- Pipelining
- Memory hierarchy
- Virtual memory
- Multicore
- Storage and I/O (brief)
- Common mistakes

## Performance

- **Iron law**: `CPU time = IC × CPI × T_clk = IC × CPI / f`.
- CPI from a mix: `CPI = Σ (fraction_i × CPI_i)`. IPC = 1 / CPI.
- Speedup of B over A: `time_A / time_B`. "X% faster" means `time_A / time_B = 1 + X/100`.
- MIPS = `f / (CPI × 10^6)`. Useless across ISAs (different IC for the same program).
- **Amdahl**: `S = 1 / ((1 − p) + p / s)`, where p is the fraction of the *original execution time* that is improved. Limit as s → ∞ is `1 / (1 − p)`.
- **Gustafson** (scaled workload): `S = (1 − p) + p·N`. Use when the problem grows with N processors.
- Power: dynamic `P = α C V² f`. Lowering V and f together cuts power roughly with the cube.
- Benchmarks: summarize ratios with the geometric mean (SPEC), times with the arithmetic mean.

Calculator: `cecalc.py cpu`, `cecalc.py amdahl`.

## ISA basics

- RISC: fixed-length instructions, load/store, many registers (RISC-V, ARM, MIPS). CISC: variable length, memory operands (x86; decoded internally into micro-ops).
- Addressing modes: immediate, register, base + displacement, PC-relative, indexed.

### RISC-V (RV32I) quick reference

| Format | Fields (bit 31 → 0) | Examples |
|---|---|---|
| R | funct7 · rs2 · rs1 · funct3 · rd · opcode | add, sub, and, sll |
| I | imm[11:0] · rs1 · funct3 · rd · opcode | addi, lw, jalr |
| S | imm[11:5] · rs2 · rs1 · funct3 · imm[4:0] · opcode | sw, sb |
| B | imm[12\|10:5] · rs2 · rs1 · funct3 · imm[4:1\|11] · opcode | beq, blt |
| U | imm[31:12] · rd · opcode | lui, auipc |
| J | imm[20\|10:1\|11\|19:12] · rd · opcode | jal |

- 32 registers, `x0` hardwired to 0. Immediates are sign-extended. B and J offsets are in multiples of 2 bytes (bit 0 implied 0).
- Loading a 32-bit constant: `lui rd, hi20` + `addi rd, rd, lo12`. If lo12 is negative as a signed 12-bit value, add 1 to hi20 first (`hi20 = (C + 0x800) >> 12`).
- ABI: `ra`=x1, `sp`=x2, `a0–a7` args/returns (x10–x17), `t0–t6` caller-saved temps, `s0–s11` callee-saved (s0 = frame pointer). Stack grows down, 16-byte aligned.
- MIPS equivalents: `$zero`, `$ra`, `$sp`, `$a0–$a3`, `$v0–$v1`, `$t0–$t9`, `$s0–$s7`; branch delay slot in classic MIPS.

## Pipelining

Classic 5-stage: IF → ID → EX → MEM → WB. Ideal CPI = 1; speedup over single-cycle is at most the number of stages (less with unbalanced stages and register overhead).

Pipelined clock period = slowest stage + pipeline register overhead.

### Hazards

| Hazard | Cause | Fix |
|---|---|---|
| Structural | Two instructions need one resource | Duplicate resource (separate I/D caches), stall |
| Data RAW | Read before earlier write completes | Forwarding (EX→EX, MEM→EX); stall when forwarding can't help |
| Data WAR/WAW | Only in out-of-order or multi-cycle pipelines | Register renaming |
| Control | Next PC unknown until branch resolves | Predict, resolve earlier, delay slot (MIPS) |

Rules for the classic 5-stage pipeline (register file writes in the first half of the cycle, reads in the second):
- **No forwarding**: a dependent instruction right after the producer stalls 2 cycles (it can read in the cycle the producer writes back).
- **Full forwarding**: ALU → ALU dependences need 0 stalls. **Load-use** needs 1 stall.
- Branch resolved in EX with predict-not-taken: taken branch costs 2 cycles. Resolved in ID: 1 cycle (needs a comparator in ID, may add a data stall).

`CPI = 1 + stall cycles per instruction`. Example: 20% loads, half followed by a dependent use (1 stall), 15% branches, 60% taken, 2-cycle penalty: `CPI = 1 + 0.2·0.5·1 + 0.15·0.6·2 = 1.28`.

Drawing a pipeline diagram (always do this for hazard questions):

```
cycle        1   2   3   4   5   6   7   8
lw  x1,0(x2) IF  ID  EX  MEM WB
add x3,x1,x4     IF  ID  --  EX  MEM WB          load-use: 1 bubble
sub x5,x3,x6         IF  --  ID  EX  MEM WB      EX→EX forward, no stall
```

### Branch prediction

- Static: always not taken; backward-taken/forward-not-taken (loops).
- 1-bit: mispredicts twice per loop execution (exit and re-entry).
- 2-bit saturating counter: states strongly/weakly taken/not-taken; mispredicts once per loop exit.
- Correlating / gshare: global history XOR PC indexes a table of 2-bit counters.
- BTB caches target addresses so a predicted-taken branch redirects fetch in IF. Return address stack predicts `ret`.
- Misprediction cost grows with pipeline depth.

### Beyond scalar in-order

- Superscalar: issue width w, ideal CPI = 1/w.
- Out-of-order: Tomasulo (reservation stations, CDB broadcast), register renaming removes WAR/WAW, reorder buffer (ROB) commits in order for precise exceptions.
- Speculation squashes wrong-path work, but microarchitectural state (caches) can leak it (Spectre).
- VLIW: compiler schedules parallel operations. SIMD/vector: one instruction, many data elements. GPU: SIMT, warps of 32 threads; divergence serializes paths.
- Multithreading: fine-grained, coarse-grained, simultaneous (SMT/Hyper-Threading).

## Memory hierarchy

Locality: temporal (reuse soon) and spatial (neighbors soon).

### Cache organization

For byte-addressed memory with address width A:

```
offset bits = log2(block size in bytes)
sets        = cache size / (block size × ways)
index bits  = log2(sets)
tag bits    = A − index − offset
```

Direct-mapped: 1 way. Fully associative: 1 set, 0 index bits. Storage per line: data + tag + valid (+ dirty for write-back, + LRU bits).

Calculator: `cecalc.py cache --size 32KiB --block 64 --assoc 8 --addr-bits 32` and add `--trace ...` to simulate an access sequence with LRU or FIFO and classify misses.

### Misses: the 3 Cs (+1)

- **Compulsory**: first access to a block (infinite cache would still miss).
- **Capacity**: the working set exceeds the cache (a fully associative cache of the same size would also miss).
- **Conflict**: too many blocks map to one set (fully associative would hit).
- **Coherence**: invalidated by another core.

Bigger blocks cut compulsory misses (spatial locality) but raise miss penalty and can raise conflict misses in small caches. More associativity cuts conflict misses but can lengthen hit time.

### Policies

- Write-through (every write goes to next level, usually with a write buffer) vs write-back (dirty bit, write on eviction).
- Write-allocate (fetch block on write miss; pairs with write-back) vs no-write-allocate (pairs with write-through).
- Replacement: LRU (exact is costly beyond 4–8 ways), pseudo-LRU (tree), FIFO, random.

### AMAT

`AMAT = hit time + miss rate × miss penalty`. Multi-level with **local** miss rates:

```
AMAT = HT_L1 + MR_L1 × (HT_L2 + MR_L2 × (HT_L3 + MR_L3 × T_mem))
```

Global miss rate of L2 = `MR_L1 × MR_L2(local)`. Memory stall cycles per instruction = `(memory accesses/instr) × miss rate × miss penalty`; add to base CPI. Remember instruction fetches are memory accesses too (1 per instruction).

Calculator: `cecalc.py amat --levels 1:0.05 10:0.2 --mem 100`.

### Optimizations

Loop interchange (walk arrays in storage order; C is row-major), blocking/tiling for matrix multiply, prefetching, victim caches, non-blocking caches (hit under miss), critical word first, way prediction.

## Virtual memory

```
page offset bits = log2(page size)
VPN bits         = VA bits − offset bits
PFN bits         = PA bits − offset bits
flat table size  = 2^VPN × PTE size
```

- Multi-level page tables save space for sparse address spaces. Levels needed when each table fits in one page: `ceil(VPN bits / log2(page size / PTE size))`. x86-64 with 4 KiB pages: 48-bit VA = 9+9+9+9+12 (4 levels).
- TLB caches translations. TLB reach = entries × page size. Huge pages raise reach.
- Effective access time with TLB (1-level table): `EAT = TLB time + mem time + TLB miss rate × mem time` (page walk adds one memory access per level on a miss).
- Page fault: OS loads the page from disk, updates the PTE, restarts the instruction. Costs millions of cycles.
- **VIPT** (virtually indexed, physically tagged) L1 avoids aliasing when index + offset bits ≤ page offset bits, i.e. `cache size / ways ≤ page size`. That is why many L1s are 32 KiB 8-way with 4 KiB pages.

Calculator: `cecalc.py vm --va-bits 48 --page 4KiB --pte 8 --tlb 64`.

## Multicore

### Coherence

- Problem: private caches hold stale copies. Invariant: single writer or multiple readers per block.
- **MSI**: Modified, Shared, Invalid. **MESI** adds Exclusive (clean, sole copy: write without a bus transaction). **MOESI** adds Owned (dirty, shared; supplies data).
- Snooping (broadcast on a shared bus; scales poorly) vs directory (tracks sharers per block; scales).
- **False sharing**: independent variables on the same cache line ping-pong between cores. Pad or align to the line size (usually 64 B).

### Memory consistency

- Sequential consistency: all cores see one interleaving respecting program order. Simple, slow.
- x86-TSO: stores can be delayed past later loads (store buffer). ARM and RISC-V (RVWMO) are weaker: most reorderings allowed.
- Fences / acquire-release atomics restore ordering. In C/C++ use `<stdatomic.h>` / `std::atomic`, not `volatile`.
- Synchronization primitives: test-and-set, compare-and-swap, load-reserved/store-conditional (LR/SC).

## Storage and I/O (brief)

- Disk access time = seek + rotational latency (half a rotation on average: 60/(2·RPM) s) + transfer + controller.
- RAID 0 (striping), 1 (mirroring), 5 (distributed parity, survives 1 disk), 6 (survives 2).
- I/O methods: polling, interrupts, DMA.

## Common mistakes

- Using lines instead of sets for index bits.
- Forgetting that miss penalty in AMAT is the *next level's* AMAT, not raw memory time, in multi-level hierarchies.
- Mixing global and local miss rates in the nested formula.
- Treating a pipeline's latency as its throughput; one instruction still takes 5 cycles, but one completes per cycle.
- Counting the load-use stall when the consumer is two instructions after the load (no stall with forwarding).
- Applying Amdahl's p to instruction counts instead of time.
