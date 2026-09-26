# Low-level programming

How numbers live in bits, where C bites, and how assembly and linking work underneath.

## Contents

- Integer representation
- IEEE 754
- Bit manipulation (C)
- C pitfalls and undefined behavior
- Assembly and calling conventions
- Build pipeline
- Tooling
- Common mistakes

## Integer representation

| n-bit | Range |
|---|---|
| unsigned | 0 … 2^n − 1 |
| two's complement | −2^(n−1) … 2^(n−1) − 1 |
| sign-magnitude, ones' complement | −(2^(n−1) − 1) … 2^(n−1) − 1 (two zeros) |

- Negate in two's complement: invert all bits, add 1. The most negative value negates to itself.
- Sign extension replicates the MSB; zero extension fills with 0.
- Unsigned overflow = carry out of the MSB. Signed overflow = operands with equal signs produce a result with a different sign.
- Hex digit = 4 bits, octal digit = 3 bits. Powers: 2^10 = 1024, 2^16 = 65 536, 2^20 ≈ 1.05 M, 2^32 ≈ 4.29 G.
- **Endianness**: little-endian stores the least significant byte at the lowest address (x86, most ARM and RISC-V configurations). Big-endian stores the MSB first (network byte order). 0x12345678 at address 0 in little-endian: bytes 78 56 34 12.
- BCD: each decimal digit in 4 bits. Gray code: `g = b ^ (b >> 1)`.

Calculator: `cecalc.py conv VALUE --bits N`.

## IEEE 754

| | sign | exponent | fraction | bias |
|---|---|---|---|---|
| half (binary16) | 1 | 5 | 10 | 15 |
| single (binary32) | 1 | 8 | 23 | 127 |
| double (binary64) | 1 | 11 | 52 | 1023 |

- Normal: `(−1)^s × 1.f × 2^(e − bias)`, stored exponent 1 … max−1.
- Exponent 0: zero (f = 0) or subnormal `0.f × 2^(1 − bias)` (gradual underflow).
- Exponent all ones: infinity (f = 0) or NaN (f ≠ 0). NaN ≠ NaN.
- Encoding by hand: convert to binary, normalize to 1.xxx × 2^E, stored exponent = E + bias, drop the leading 1, round the fraction to nearest-even.
- 0.1, 0.2, 0.3 are not exactly representable; `0.1 + 0.2 != 0.3` in double. Compare with a tolerance.
- Single precision: about 7 decimal digits; integers exact up to 2^24. Double: about 15–16 digits; integers exact up to 2^53.
- Floating-point addition is not associative.

Calculator: `cecalc.py float 0.1`, `cecalc.py float 0x3F800000 --hex`.

## Bit manipulation (C)

```c
x |=  (1u << n);            // set bit n
x &= ~(1u << n);            // clear bit n
x ^=  (1u << n);            // toggle bit n
(x >> n) & 1u               // test bit n
(x >> lo) & ((1u << w) - 1) // extract w-bit field starting at lo
x = (x & ~(mask << lo)) | ((v & mask) << lo);  // insert field
x & (x - 1)                 // clear lowest set bit; == 0 iff x is 0 or a power of two
x & -x                      // isolate lowest set bit (unsigned x)
(x + a - 1) & ~(a - 1)      // round up to multiple of a (a = power of two)
__builtin_popcount(x), __builtin_ctz(x), __builtin_clz(x)   // GCC/Clang; ctz/clz undefined for 0
```

Use `1u` or `UINT32_C(1)`, not `1`: `1 << 31` overflows a signed int.

## C pitfalls and undefined behavior

Undefined behavior (the compiler may assume it never happens and optimize accordingly):
- signed integer overflow
- shift count negative or ≥ width of the (promoted) type; left-shifting a negative value
- out-of-bounds array access, including forming a pointer more than one past the end
- dereferencing null, dangling, or misaligned pointers
- reading uninitialized automatic variables
- strict aliasing violations (accessing an object through an incompatible pointer type; use `memcpy` or `unsigned char*`)
- data races between threads
- modifying a string literal; modifying an object twice without a sequence point (`i = i++`)

Conversions:
- **Integer promotion**: `char`, `short`, `uint8_t`, `uint16_t` become `int` in arithmetic. `uint8_t a = 200, b = 100; a + b` is 300 (int), not 44.
- **Usual arithmetic conversions**: mixing signed and unsigned of the same rank converts to unsigned. `-1 < 0u` is false. `for (unsigned i = n - 1; i >= 0; i--)` never ends.
- `sizeof` returns `size_t` (unsigned).
- `char` signedness is implementation-defined.

Structs: members are aligned to their natural alignment; padding is inserted. `struct { char c; int i; char d; }` is typically 12 bytes; reorder largest-first to shrink it. Bit-field layout is implementation-defined; do not use bit-fields to map hardware registers portably.

Qualifiers:
- `volatile`: every access happens, in order, as written. Needed for memory-mapped registers and variables changed by ISRs or signal handlers. Not atomic, no inter-core ordering.
- `const volatile`: read-only register the hardware changes (status register).
- `restrict`: promise of no aliasing, enables optimization.

Memory layout of a process: `.text` (code), `.rodata` (constants), `.data` (initialized globals), `.bss` (zero-initialized globals), heap (grows up), stack (grows down).

## Assembly and calling conventions

| ABI | Args | Return | Callee-saved | Notes |
|---|---|---|---|---|
| RISC-V | a0–a7 | a0, a1 | s0–s11, sp | ra holds return address |
| ARM32 AAPCS | r0–r3 | r0, r1 | r4–r11, sp | lr = r14, pc = r15; 8-byte stack alignment at calls |
| AArch64 | x0–x7 | x0 | x19–x28, sp | x29 = FP, x30 = LR; 16-byte stack alignment |
| x86-64 System V | rdi, rsi, rdx, rcx, r8, r9 | rax (rdx:rax) | rbx, rbp, r12–r15 | rsp 16-byte aligned before `call`; 128-byte red zone |
| x86-64 Windows | rcx, rdx, r8, r9 | rax | rbx, rbp, rdi, rsi, r12–r15 | 32-byte shadow space |

Function prologue/epilogue in RISC-V:

```asm
# int sum(int *a, int n): returns a[0] + ... + a[n-1]
sum:
    li   t0, 0          # t0 = total
    beqz a1, done       # n == 0 -> return 0
loop:
    lw   t1, 0(a0)      # t1 = *a
    add  t0, t0, t1     # total += *a
    addi a0, a0, 4      # a++ (int is 4 bytes)
    addi a1, a1, -1     # n--
    bnez a1, loop
done:
    mv   a0, t0         # return value in a0
    ret                 # jalr x0, 0(ra)
```

A leaf function that uses only temporaries needs no stack frame. A non-leaf must save `ra` (and any `s` registers it uses) on the stack:

```asm
    addi sp, sp, -16
    sw   ra, 12(sp)
    sw   s0, 8(sp)
    ...
    lw   s0, 8(sp)
    lw   ra, 12(sp)
    addi sp, sp, 16
    ret
```

Recursion questions: draw the stack frames, one per active call, with saved `ra` and locals.

## Build pipeline

`preprocess (cpp) → compile (cc1) → assemble (as) → link (ld)`

- Object files hold sections and a symbol table with relocations. `nm` lists symbols, `objdump -d` disassembles, `readelf -a` dumps ELF headers.
- "undefined reference" = linker error (missing definition or library). "implicit declaration" = compiler warning (missing prototype; treat as an error).
- Static linking copies code into the executable. Dynamic linking resolves at load/run time through the PLT/GOT.
- Embedded targets use a linker script to place `.text` in flash and `.data`/`.bss` in RAM.

## Tooling

- Compile with warnings: `-Wall -Wextra -Wconversion -Wshadow`.
- Sanitizers on a host build: `-fsanitize=address,undefined -g`.
- `gdb`: `break`, `run`, `next`, `step`, `bt`, `info registers`, `x/16xw addr`, `watch var`.
- Valgrind (memcheck) for leaks and invalid accesses.
- Compiler Explorer (godbolt.org) to see what the compiler emits at each optimization level.

## Common mistakes

- `int` assumed to be 32 bits on every platform (it is 16 on AVR). Use `<stdint.h>`.
- Printing `size_t` with `%d` (use `%zu`), `uint32_t` with `%u` on platforms where it is `unsigned long` (use `PRIu32`).
- Returning a pointer to a local variable.
- Off-by-one in `malloc(strlen(s))` (needs + 1 for the terminator).
- Treating `sizeof(array)` inside a function as the array size (it is the pointer size).
