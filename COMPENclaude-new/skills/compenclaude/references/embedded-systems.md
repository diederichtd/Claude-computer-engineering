# Embedded systems

Microcontroller firmware from reset vector to RTOS, with the bus, timer, and ADC details that cause most bugs.

Part-specific details (register names, bit positions, electrical limits) vary between vendors and even between chips in one family. Give the general mechanism, then tell the user which reference-manual or datasheet section to confirm.

## Contents

- Microcontroller anatomy
- GPIO
- Interrupts
- Timers and PWM
- Serial buses
- ADC and DAC
- DMA
- RTOS concepts
- Low power
- Debugging firmware
- Firmware bug checklist

## Microcontroller anatomy

- CPU core (Cortex-M0/M3/M4/M7, RISC-V, AVR), flash (code, constants), SRAM (data, stack, heap), memory-mapped peripherals, clock tree (internal RC, external crystal, PLL), reset and power management.
- Peripherals only work once their **clock is enabled** (e.g. STM32 `RCC->AHB1ENR`). Forgetting this is the most common "register writes do nothing" bug.
- Memory-mapped I/O in C:

```c
#define GPIOA_ODR (*(volatile uint32_t *)0x40020014u)
GPIOA_ODR |= (1u << 5);   // read-modify-write; not atomic if an ISR also writes it
```

Prefer atomic set/reset registers when the part has them (STM32 `BSRR`, AVR `PINx` write-to-toggle).

### Startup sequence (bare metal)

1. Reset: the core loads the initial SP and the reset handler address from the vector table (Cortex-M: words 0 and 1).
2. Reset handler copies `.data` initial values from flash to RAM, zeroes `.bss`, optionally sets up clocks and the FPU.
3. Calls C++ static constructors (if any), then `main()`.
4. `main` must never return on bare metal; end with an infinite loop.

## GPIO

- Modes: input (floating, pull-up, pull-down), output push-pull, output open-drain, alternate function, analog.
- **Push-pull** drives both high and low. **Open-drain** only pulls low; needs a pull-up; lets several devices share a line (I2C, wired-AND interrupts).
- Floating inputs pick up noise; always pull or drive unused inputs.
- Pin current limits are per pin and per port (often ~20 mA per pin, less in total). Use a transistor for loads beyond that.
- **Debouncing** mechanical switches: bounce lasts about 1–20 ms. Debounce in software (sample every 5–10 ms, accept after N stable samples) or with RC + Schmitt trigger.

## Interrupts

Rules for ISRs:
1. Keep them short: clear the flag, move data, set a flag or push to a queue, return. Do the work in the main loop or a task.
2. Share data through `volatile` variables. For multi-byte data on an 8-bit MCU, or read-modify-write sequences, disable interrupts around the access in the main code (critical section) or use atomics.
3. No blocking calls, no `delay()`, no `printf`, no `malloc` inside an ISR.
4. Clear the interrupt source flag, or the ISR re-enters forever. Some flags clear on read of a data register; check the manual.
5. Cortex-M NVIC: lower number = higher priority. Only interrupts with priority numerically ≥ `configMAX_SYSCALL_INTERRUPT_PRIORITY` may call FreeRTOS `...FromISR` APIs.

Latency = hardware entry (Cortex-M: 12 cycles typical) + time spent in higher-priority ISRs + time interrupts are disabled.

```c
static volatile uint32_t ticks;

void SysTick_Handler(void) { ticks++; }

uint32_t get_ticks(void) {
    return ticks;           // 32-bit aligned read is atomic on 32-bit cores
}

// Wrap-safe timeout check (works across counter overflow):
if ((uint32_t)(get_ticks() - start) >= timeout_ms) { ... }
```

## Timers and PWM

- Tick frequency: `f_tick = f_timer_clk / prescaler`. Counter runs 0 … reload, so **period = (reload + 1) / f_tick**.
- STM32: `PSC` register holds prescaler − 1, `ARR` holds reload. AVR CTC mode: `OCRnA` holds reload.
- PWM: duty = compare / (reload + 1). Resolution in bits = log2(reload + 1). Higher PWM frequency means lower resolution for a fixed clock.
- Input capture measures periods/pulse widths; output compare schedules edges.
- Watchdog: must be refreshed periodically; refresh it from the main loop after checking that all tasks are alive, never from a timer ISR alone.

Calculator: `cecalc.py timer --clock 16MHz --target 1kHz --bits 16 --prescalers 1,8,64,256,1024`.

## Serial buses

| | UART | SPI | I2C | CAN |
|---|---|---|---|---|
| Wires | TX, RX (+GND) | SCLK, MOSI/COPI, MISO/CIPO, CS per device | SDA, SCL | CANH, CANL (differential) |
| Clock | none (agreed baud) | from controller | from controller | none (bit timing) |
| Duplex | full | full | half | half |
| Addressing | point-to-point | chip-select lines | 7-bit (or 10-bit) address | message ID (priority) |
| Typical speed | 9600–921600 baud | 1–50+ MHz | 100 k / 400 k / 1 M / 3.4 MHz | 125 k–1 Mbps (CAN FD data phase faster) |
| Gotchas | baud error, TX↔RX crossed, voltage levels (RS-232 is ±V) | mode (CPOL/CPHA), CS timing, MSB/LSB first | pull-ups required, address shifted by 1 bit in some APIs, bus lock-up | 120 Ω termination at **both** ends, transceiver needed |

UART details:
- Frame 8N1 = start + 8 data + stop = 10 bits. Throughput = baud / 10 bytes/s.
- Receiver resynchronizes on each start bit; total baud mismatch between the two sides should stay under about 2%.
- Idle line is high. A "break" holds the line low longer than a frame.

SPI modes: mode 0 (CPOL 0, CPHA 0) and mode 3 (CPOL 1, CPHA 1) are most common. Sample edge: mode 0 samples on the rising edge.

I2C details:
- Start: SDA falls while SCL is high. Stop: SDA rises while SCL is high. Data changes only while SCL is low.
- After each byte, the receiver drives ACK (low) or NACK (high).
- Address byte = 7-bit address << 1 | R/W. Datasheets list either the 7-bit address (0x50) or the 8-bit write address (0xA0); libraries differ in which they expect.
- Pull-up value: small enough for rise time (bus capacitance), large enough that devices can sink the current (3 mA at standard/fast mode). 4.7 kΩ at 100 kHz, 2.2 kΩ at 400 kHz are common starting points.
- Clock stretching: a target holds SCL low to pause the controller.
- Bus stuck low after a reset mid-transfer: toggle SCL up to 9 times, then send a stop.

Calculator: `cecalc.py baud --clock 16MHz --baud 115200`.

## ADC and DAC

- LSB = Vref / 2^N. A 10-bit ADC at 5 V: 4.88 mV per step. At 3.3 V: 3.22 mV.
- Code = floor(Vin / LSB), clamped to 2^N − 1.
- Sample at more than twice the highest signal frequency (Nyquist); add an anti-aliasing low-pass filter before the ADC.
- SAR ADCs sample onto a capacitor: the source impedance must let it settle within the sampling time. Buffer high-impedance sources or lengthen the sample time.
- Effective resolution is lower than N bits because of noise: ENOB = (SINAD − 1.76) / 6.02.
- Averaging 4^k samples adds about k bits of resolution when noise is present (oversampling).
- A voltage divider for measuring a battery: pick resistors so Vin stays below Vref at max input; high values reduce drain but raise source impedance.

Calculator: `cecalc.py adc --bits 12 --vref 3.3V --volts 1.2`.

## DMA

Moves data between peripherals and memory without the CPU. Configure source, destination, count, increment modes, and trigger. Common uses: UART RX into a circular buffer, ADC scan into an array, SPI display updates. Watch cache coherence on cores with data caches (Cortex-M7): clean/invalidate the buffer or place it in non-cacheable memory.

## RTOS concepts

- Tasks with priorities; the scheduler runs the highest-priority ready task (preemptive). Equal priorities round-robin on tick.
- **Mutex** (ownership, priority inheritance, for protecting a resource) vs **binary semaphore** (signaling, e.g. ISR → task) vs **counting semaphore** (pool of N resources) vs **queue** (pass data).
- **Priority inversion**: low task holds a mutex, high task waits, medium task preempts low. Fix: priority inheritance (mutexes in FreeRTOS do this; semaphores do not).
- Deadlock: acquire locks in a fixed global order.
- Stack per task: size it from worst-case call depth plus ISR frames; enable stack overflow checking during development.
- From an ISR use only `...FromISR` APIs and request a context switch if a higher-priority task woke.
- Rate-monotonic scheduling: shorter period → higher priority. Schedulable for n tasks if `Σ Ci/Ti ≤ n(2^(1/n) − 1)` (sufficient, not necessary; about 0.69 as n → ∞).

## Low power

- Sleep modes trade wake-up time for current: run → sleep (core stopped) → stop (clocks off, RAM kept) → standby/deep sleep (most state lost).
- Average current = Σ (current_i × time_i) / period. Battery life (hours) ≈ capacity (mAh) / average current (mA), derated for temperature, self-discharge, and cut-off voltage.
- Turn off unused peripheral clocks, configure unused pins as analog or with a defined level, lower the clock, batch work.
- Dynamic CMOS power ∝ C V² f.

## Debugging firmware

- SWD/JTAG with a debugger (ST-Link, J-Link, CMSIS-DAP): breakpoints, watchpoints, register view.
- Logic analyzer for protocol timing and decoding; oscilloscope for analog levels, rise times, ringing, noise.
- Toggle a GPIO at ISR entry/exit to measure timing on a scope.
- Cortex-M HardFault: read the stacked PC and LR, plus CFSR/HFSR/MMFAR/BFAR registers, to find the faulting instruction. Common causes: null pointer, stack overflow, unaligned access, executing from invalid memory, division by zero with trapping enabled.

## Firmware bug checklist

1. Peripheral clock enabled? Pin in the right mode and alternate function?
2. Interrupt enabled at the peripheral **and** in the NVIC, and globally?
3. Flag cleared in the ISR?
4. Shared variables `volatile`, accesses atomic?
5. Stack large enough? (Random crashes after adding a local array.)
6. Correct clock frequency assumed in baud/timer math? (HSI vs HSE vs PLL.)
7. Voltage levels compatible (3.3 V MCU talking to a 5 V device)?
8. Common ground between boards?
9. Watchdog resetting the chip silently?
10. Compiler optimization removing a delay loop or merging register accesses (missing `volatile`)?
