# Digital logic and HDL

Boolean algebra through synthesizable HDL: the rules, timing equations, and templates for designing and checking digital circuits.

## Contents

- Boolean algebra
- Combinational building blocks
- Sequential logic
- Finite state machines
- Verilog / SystemVerilog rules
- FPGA notes
- Common mistakes

## Boolean algebra

- Identities: `A + A'B = A + B`, `A(A + B) = A`, `A + AB = A`, consensus `AB + A'C + BC = AB + A'C`.
- De Morgan: `(AB)' = A' + B'`, `(A + B)' = A'B'`. NAND and NOR are each functionally complete.
- XOR: `A ⊕ B = A'B + AB'`; parity of n bits = XOR of all bits; `A ⊕ A = 0`, `A ⊕ 0 = A`.
- Canonical forms: SOP = OR of minterms Σm(...), POS = AND of maxterms ΠM(...). Minterm indices of F are the maxterm indices of F'.

### K-maps
- Rows/columns in Gray order (00, 01, 11, 10); edges wrap.
- Groups are rectangles of size 2^k. Make groups as large as possible, use as few as possible. Every 1 covered at least once.
- Don't-cares (X) may join groups but never need covering.
- Essential prime implicant: the only group covering some 1. Take those first.
- Hazards: a static-1 hazard exists when two adjacent 1s are covered by different groups with no group spanning both. Add the consensus term to remove it (only matters in asynchronous logic or glitch-sensitive outputs).

## Combinational building blocks

| Block | Notes |
|---|---|
| 2^n:1 mux | n select lines. Any n-input function fits in a 2^n:1 mux (inputs tied to 0/1), or in a 2^(n−1):1 mux with the last variable fed to data inputs as 0, 1, x, x'. |
| n:2^n decoder | One-hot outputs; with an OR gate per output it implements any SOP. |
| Priority encoder | Output index of highest-priority active input plus a valid bit. |
| Ripple-carry adder | n full adders. Delay O(n): about 2n gate delays on the carry chain. |
| Carry-lookahead | g = ab, p = a ⊕ b (or a + b); `c(i+1) = g(i) + p(i)c(i)`. Delay O(log n) with a tree. |
| Carry-select | Compute both carry-in cases, mux on real carry. |
| Subtractor | `A − B = A + B' + 1`: invert B, set carry-in to 1. |
| Comparator | Equality: XNOR per bit then AND. Magnitude: subtract and check sign/carry (unsigned: borrow = NOT carry-out). |

Full adder: `s = a ⊕ b ⊕ cin`, `cout = ab + cin(a ⊕ b)`.

Overflow in two's complement addition: `V = c(n) ⊕ c(n−1)` (carry into MSB XOR carry out of MSB).

## Sequential logic

- **Latch**: level-sensitive (transparent while enable is active). **Flip-flop**: edge-triggered.
- D FF: `Q+ = D`. JK: `Q+ = JQ' + K'Q`. T: `Q+ = T ⊕ Q`. SR latch with S = R = 1 is invalid (NOR form).
- Registers, shift registers, counters (binary, ring = one-hot rotating, Johnson = inverted feedback, 2n states from n FFs).

### Timing

Parameters: `t_cq` (clock-to-Q), `t_pd` (max combinational delay), `t_cd` (min/contamination delay), `t_setup`, `t_hold`, `t_skew`.

- Setup (max delay): `T_clk ≥ t_cq + t_pd + t_setup (+ t_skew if the capture clock arrives early)`. So `f_max = 1 / (t_cq + t_pd + t_setup)`.
- Hold (min delay): `t_cq(min) + t_cd ≥ t_hold (+ t_skew if the capture clock arrives late)`. Hold does not depend on the clock period; lowering the frequency does not fix a hold violation. Add delay on the short path instead.
- Critical path: the longest register-to-register path. Pipelining splits it and raises f_max at the cost of latency and register overhead.

Worked example: `t_cq = 50 ps`, longest logic 400 ps, `t_setup = 30 ps` → `T_min = 480 ps` → `f_max ≈ 2.08 GHz`.

### Metastability and clock domain crossing (CDC)

- A flop sampling an asynchronous input can go metastable. A 2-flop synchronizer gives it a full cycle to resolve; MTBF grows exponentially with resolve time (`MTBF = e^(t_r/τ) / (T_0 · f_clk · f_data)`).
- Single-bit level signal: 2-FF (or 3-FF at high speed) synchronizer in the destination domain.
- Single-cycle pulse into a slower domain: convert to a toggle, synchronize, edge-detect. Or use a handshake.
- Multi-bit data: never synchronize bits independently (they can arrive in different cycles). Use Gray-coded counters (only one bit changes per step), a req/ack handshake with data held stable, or an asynchronous FIFO (Gray-coded pointers synchronized across).
- Asynchronous reset: assert asynchronously, **deassert synchronously** (reset synchronizer), or flops may leave reset on different cycles.

## Finite state machines

- **Moore**: outputs depend only on state (glitch-free, one cycle later). **Mealy**: outputs depend on state and inputs (fewer states, faster reaction, can glitch).
- Design steps: state diagram → state table → encoding → next-state and output equations (K-maps) → circuit. Check every state handles every input combination.
- Encodings: binary (⌈log2 N⌉ FFs), one-hot (N FFs, simple fast next-state logic, common on FPGAs), Gray (one bit changes per transition in sequential FSMs).
- Sequence detectors: decide overlapping vs non-overlapping before drawing states. "1011" overlapping needs 4 states in Mealy form, 5 in Moore.
- Unused states: send them to reset/idle for safety.

## Verilog / SystemVerilog rules

1. Sequential logic: `always_ff @(posedge clk)` with nonblocking `<=`. Combinational: `always_comb` with blocking `=`.
2. In `always_comb`, assign every output on every path. Put defaults at the top. Otherwise a latch is inferred.
3. `case` inside `always_comb`: add a `default`. Use `unique case` / `priority case` only when you mean it.
4. Declare explicit widths: `8'd5`, `4'b1010`. Unsized constants are 32 bits. Watch width truncation warnings.
5. Arithmetic is unsigned unless *all* operands are `signed`. Use `$signed()` deliberately.
6. Do not drive one signal from two `always` blocks.
7. `#delay`, `initial` (for ASIC), `$display`, and `forever` do not synthesize. FPGA tools do accept `initial` for register init values.
8. Use `logic` in SystemVerilog instead of choosing between `wire` and `reg`.
9. Avoid combinational loops and gated clocks; use clock enables.
10. Parameterize widths (`parameter int W = 8`) and use `generate` for replication.

### FSM template (SystemVerilog)

```systemverilog
module seq_1011 (
  input  logic clk, rst_n, din,
  output logic hit           // Moore: high for one cycle after "1011" (overlapping)
);
  typedef enum logic [2:0] {S0, S1, S10, S101, S1011} state_t;
  state_t state, next;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) state <= S0;
    else        state <= next;

  always_comb begin
    next = state;                       // default: hold (prevents latches)
    unique case (state)
      S0:    next = din ? S1    : S0;
      S1:    next = din ? S1    : S10;
      S10:   next = din ? S101  : S0;
      S101:  next = din ? S1011 : S10;
      S1011: next = din ? S1    : S10;  // overlap: "1" or "10" suffix reused
      default: next = S0;
    endcase
  end

  assign hit = (state == S1011);
endmodule
```

### Self-checking testbench skeleton

```systemverilog
module tb;
  logic clk = 0, rst_n = 0, din = 0, hit;
  seq_1011 dut (.*);
  always #5 clk = ~clk;

  task automatic send(input logic b); din = b; @(posedge clk); #1; endtask

  initial begin
    repeat (2) @(posedge clk); rst_n = 1;
    send(1); send(0); send(1); send(1);
    assert (hit) else $error("missed first 1011");
    send(0); send(1); send(1);
    assert (hit) else $error("missed overlapping 1011");
    $display("done"); $finish;
  end
endmodule
```

### VHDL reminders

- Clocked process: `if rising_edge(clk) then ... end if;`. Signals update at process end; variables update immediately.
- Use `numeric_std` (`unsigned`, `signed`), never `std_logic_arith`.
- Combinational process: complete sensitivity list (or `process(all)` in VHDL-2008) and assign all outputs.

## FPGA notes

- LUT-based: a k-input LUT (k = 4 to 6) implements any k-input function in one level.
- Block RAM is usually synchronous read: data appears one cycle after the address. Write HDL that matches the template so the tool infers BRAM.
- DSP slices do multiply-accumulate; pipeline registers around them reach higher f_max.
- Always write timing constraints (clock period, I/O delays); read the timing report for negative slack.

## Common mistakes

- Counting states vs flip-flops: N states need ⌈log2 N⌉ flip-flops in binary encoding.
- Forgetting that a Moore output lags the input by a cycle.
- Using `<=` in combinational blocks (works in simple cases, confuses readers, breaks with intermediate variables).
- Believing a lower clock fixes hold violations.
- Synchronizing a counter bus with per-bit 2-FF synchronizers.
- Assuming simulation equals hardware when there are latches, uninitialized regs (X), or missing constraints.
