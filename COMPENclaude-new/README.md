# COMPENclaude

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that makes Claude precise on computer engineering problems.

In computer engineering, one wrong bit index or one missing stall cycle makes the whole answer wrong. General-purpose AI slips on exactly these details. COMPENclaude gives Claude the method, the reference material, and an exact calculator that a senior engineer and a good teaching assistant would bring: it states the assumptions that change the answer, shows the formula with units, computes the numbers instead of guessing them, and checks the result before replying.

## What it does

| Feature | What happens |
|---|---|
| **States assumptions first** | Word size, endianness, forwarding, write policy, KB vs KiB: the details that decide whether an answer matches your textbook |
| **Exact calculations** | A built-in calculator handles two's complement, IEEE 754, cache geometry, AMAT, CPU time, Amdahl, paging, subnets, timers, baud rates, ADCs, RC circuits, Hamming codes, and CRC |
| **Cache simulator** | Runs an address trace through LRU or FIFO and labels every miss as compulsory, capacity, or conflict |
| **Pipeline diagrams** | Draws cycle-by-cycle charts and counts stalls under the forwarding model you name |
| **Correct HDL** | Synthesizable SystemVerilog with no latches, proper reset, explicit widths, and a self-checking testbench |
| **Safe firmware** | Embedded C with `volatile` where it belongs, atomic shared data, short ISRs, and no undefined behavior |
| **Trap checklist** | 22 classic mistakes, from off-by-one bit ranges to `if` around condition variable waits, checked on every answer |
| **Debugging help** | Ranks likely causes, says how to confirm each one with a scope or logic analyzer, then gives the fix |
| **Teaching mode** | For students: intuition, formal rule, worked example, common mistake, then a practice question |
| **Design reviews** | Checklists for HDL and firmware, plus templates for lab reports, debug logs, and exam formula sheets |
| **Corrects wrong premises** | Says so when a question assumes something false, like "volatile makes it thread-safe" |

**Topics:** Boolean algebra, K-maps, FSMs, setup and hold timing, clock domain crossing, Verilog, SystemVerilog, VHDL, FPGAs, RISC-V, pipelining, branch prediction, out-of-order execution, caches, virtual memory, cache coherence, memory consistency, C and assembly, calling conventions, linking, microcontrollers, interrupts, timers, UART, SPI, I2C, CAN, ADCs, DMA, RTOS, low power, scheduling, synchronization, deadlock, page replacement, file systems, subnetting, TCP, error-correcting codes, MOSFET switches, and CMOS logic.

## Install

### Claude.ai or the Claude desktop app

1. Download `compenclaude.zip` from the [Releases](../../releases) page, or build it yourself:
   ```bash
   cd skills && zip -r ../compenclaude.zip compenclaude -x '*/__pycache__/*' '*.DS_Store'
   ```
2. In Claude, open **Settings** and find **Skills** (under Capabilities or Customize, depending on your app version). Code execution needs to be turned on for skills to work.
3. Click **Upload skill** and choose `compenclaude.zip`.
4. Make sure the skill is toggled on.

### Claude Code (as a plugin)

```bash
/plugin marketplace add diederichtd/COMPENclaude
```

```bash
/plugin install compenclaude@compenclaude
```

### Claude Code (manual copy)

```bash
git clone https://github.com/diederichtd/COMPENclaude.git
```

```bash
mkdir -p ~/.claude/skills && cp -r COMPENclaude/skills/compenclaude ~/.claude/skills/
```

For one project only, copy it to `.claude/skills/` inside that project instead.

## How to use it

Ask Claude the way you'd ask a TA or a senior engineer. The skill turns on by itself when a question touches computer engineering. Some examples:

- "32 KiB 8-way cache, 64-byte blocks, 32-bit addresses. Which set does 0x1234ABCD go to?"
- "How many stalls does this RISC-V code have on a 5-stage pipeline with forwarding?"
- "Encode −13.625 as an IEEE 754 single and explain each field."
- "Write a synthesizable SystemVerilog UART transmitter with a testbench."
- "My STM32 I2C read hangs at the busy flag. What should I check?"
- "Split 10.20.0.0/22 into subnets for 200, 100, 50 and 2 hosts."
- "I don't get setup and hold time. Exam next week."

Tips:

- Name your textbook or course conventions if you know them (where branches resolve, which ADC formula your class uses). Claude will match them.
- Give the part number for hardware questions. Register names and limits differ between chips.
- Paste your own attempt. Claude can point to the exact step that went wrong.

## How it works

A skill is a folder with a `SKILL.md` file that Claude reads when a task matches the skill's description. Claude loads only the short description at first, then the full instructions when the skill triggers, and each reference file only when a question needs it. A subnetting question never loads the Verilog rules.

```
COMPENclaude/
├── CLAUDE.md                    # instructions for Claude Code when working on this repo
├── .claude-plugin/
│   ├── plugin.json              # Claude Code plugin manifest
│   └── marketplace.json         # lets people install with /plugin
├── skills/
│   └── compenclaude/            # the skill itself (this is what you zip)
│       ├── SKILL.md             # method, routing table, trap checklist, modes
│       ├── references/          # loaded only when needed
│       │   ├── digital-logic.md
│       │   ├── computer-architecture.md
│       │   ├── low-level-programming.md
│       │   ├── embedded-systems.md
│       │   ├── operating-systems.md
│       │   ├── networking.md
│       │   └── circuits-electronics.md
│       ├── assets/templates/    # review checklist, debug log, lab report, formula sheet, HDL module and testbench
│       └── scripts/
│           └── cecalc.py        # exact calculators with worked output
├── docs/                        # the whole skill as one document (Markdown, HTML, PDF)
├── evals/evals.json             # test prompts for checking skill behavior
├── tests/                       # known-answer tests for the calculator
├── tools/
│   ├── validate_skill.py        # checks SKILL.md and manifests
│   └── build_docs.py            # rebuilds the docs/ document
└── .github/workflows/validate.yml
```

### The calculator

Works with Python 3.9 or newer and needs no extra packages. Every command prints its working.

```bash
python3 skills/compenclaude/scripts/cecalc.py float 0.1
```

```
IEEE 754 single (binary32): 1 sign, 8 exponent (bias 127), 23 fraction bits
  hex                     0x3DCCCCCD
  fields s|exp|frac       0 | 01111011 | 10011001100110011001101
  class                   normal
  exponent                stored 123, unbiased -4
  value                   +1.10011001100110011001101 (binary) x 2^-4
  exact stored value      0.100000001490116119384765625
  ...
  rounding error          -1.490116E-9
```

```bash
python3 skills/compenclaude/scripts/cecalc.py cache --size 64 --block 16 --addr-bits 8 --trace 0x00 0x10 0x40 0x00 0x80 0x04 0x50 0x10
```

```
    #       address         tag    set   off  result  evicted tag  miss type
    1           0x0         0x0      0     0  MISS                 compulsory
    2          0x10         0x0      1     0  MISS                 compulsory
    3          0x40         0x1      0     0  MISS            0x0  compulsory
    4           0x0         0x0      0     0  MISS            0x1  conflict
    ...
  hits 0/8 (0.00%), misses 8 (compulsory 5, capacity 1, conflict 2)
```

| Command | What it does |
|---|---|
| `conv` | bases, two's complement, Gray code, byte order in memory |
| `float` | IEEE 754 encode/decode, exact stored value, rounding error, ULP |
| `cache` | tag/index/offset split, storage overhead, LRU/FIFO trace simulation with miss types |
| `amat` | multi-level average memory access time with global miss rates |
| `cpu` | CPU time from instruction count, CPI or instruction mix, and clock |
| `amdahl` | overall speedup, or the speedup needed to reach a target |
| `vm` | page offset and VPN bits, page-table size, number of levels, TLB reach |
| `subnet` | network, broadcast, host range, splitting, prefix for N hosts |
| `timer` | prescaler and reload values for a target frequency, with error |
| `baud` | UART divisor, actual baud rate, error, AVR and STM32 register values |
| `adc` | LSB size, code to voltage and back, quantization error, ideal SNR |
| `rc` | time constant, cutoff frequency, rise time, charge after time t |
| `hamming` | encode data bits, or check and correct a codeword |
| `crc` | CRC remainder by mod-2 division |

Run `python3 skills/compenclaude/scripts/cecalc.py <command> -h` for options.

## Full documentation

Everything in the skill, combined into one document with a contents page: the method, all seven reference guides, the templates, and the calculator source.

- [docs/COMPENclaude.pdf](docs/COMPENclaude.pdf) to read or print
- [docs/COMPENclaude.md](docs/COMPENclaude.md) as a single Markdown file

## Development

Run the tests and the validator before opening a pull request:

```bash
python3 -m unittest discover tests
```

```bash
pip install pyyaml && python3 tools/validate_skill.py
```

GitHub Actions runs both on every push and pull request.

After editing the skill, rebuild the combined document:

```bash
python3 tools/build_docs.py --pdf
```

To check how the skill behaves, try the prompts in `evals/evals.json` with the skill on and off and compare the answers.

## Contributing

Contributions are welcome: traps Claude still falls into, new calculator commands, better reference material, templates, or fixes. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Limitations

- Claude can make mistakes. Check important results, especially anything that goes into hardware.
- Part-specific facts (register names, electrical ratings) vary by chip. The skill points you to the datasheet section to confirm them.
- Courses use different conventions for pipelines, scheduling tie-breaks, and ADC formulas. The skill makes Claude say which one it uses so you can match your class.
- It doesn't replace simulation, a logic analyzer, or your reference manual. Follow your school's rules on AI use for graded work.

## License

[MIT](LICENSE)
