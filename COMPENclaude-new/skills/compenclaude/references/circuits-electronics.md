# Circuits and electronics for computer engineers

The analog and board-level electronics a computer engineer needs to interface chips safely.

## Contents

- Fundamentals
- RC circuits
- Diodes and LEDs
- Transistors as switches
- CMOS logic
- Logic levels and interfacing
- Power and board-level practice
- Measurement tips
- Common mistakes

## Fundamentals

- Ohm: `V = I R`. Power: `P = V I = I² R = V² / R`. Check resistor power rating (1/4 W is common for through-hole, 1/10 W or less for small SMD).
- KCL: currents into a node sum to zero. KVL: voltages around a loop sum to zero.
- Series: `R = R1 + R2`. Parallel: `R = R1 R2 / (R1 + R2)`. Capacitors combine the opposite way.
- Voltage divider: `Vout = Vin × R2 / (R1 + R2)` (unloaded). A load in parallel with R2 lowers Vout; keep load impedance ≫ R2.
- Thevenin: any linear two-terminal network = voltage source + series resistance.
- Units: mA × kΩ = V. µF × kΩ = ms.

## RC circuits

- Time constant `τ = R C`. Charging: `v(t) = V_final (1 − e^(−t/τ))`; 63.2% at τ, 86.5% at 2τ, 95% at 3τ, 99.3% at 5τ.
- 10–90% rise time ≈ 2.2 τ.
- First-order low-pass cutoff: `f_c = 1 / (2π R C)`; −20 dB/decade above it.
- RC delay on long wires and loaded outputs limits edge rates; capacitive load slows logic.

Calculator: `cecalc.py rc --r 10k --c 100nF --t 1ms`.

## Diodes and LEDs

- Silicon diode forward drop ≈ 0.6–0.7 V; Schottky ≈ 0.2–0.4 V. LEDs 1.8–3.3 V depending on color.
- LED resistor: `R = (V_supply − V_f) / I_LED`. 3.3 V supply, red LED (V_f 2.0 V), 10 mA → 130 Ω (use 150 Ω).
- Flyback diode across relay coils and motors (reverse-biased in normal operation) clamps the inductive kick when the switch opens.
- Zener: regulates reverse voltage; TVS diodes clamp ESD and surges.

## Transistors as switches

**N-channel MOSFET, low side** (load between supply and drain, source to ground):
- Turns on when V_GS exceeds the threshold by enough. `V_GS(th)` is where it *starts* to conduct (e.g. 250 µA), not fully on. Check R_DS(on) at your actual gate voltage.
- With a 3.3 V MCU pin, pick a **logic-level** MOSFET with R_DS(on) specified at V_GS = 2.5 V or 3.3 V (e.g. AO3400-class parts, not IRF540N).
- Add a gate pull-down (10–100 kΩ) so the load stays off while the MCU pin floats during reset, and optionally a small gate resistor (tens of Ω) to limit ringing.
- Power dissipated ≈ I² × R_DS(on) when fully on.

**P-channel MOSFET, high side**: turns on when the gate is pulled below the source. Driving from an MCU when the load supply is above the MCU voltage needs an NPN or N-MOSFET level shifter on the gate.

**NPN BJT as switch**: saturate it. `I_B ≥ I_C / β_min × (2 to 5)` for margin. `R_B = (V_pin − 0.7) / I_B`. Example: 100 mA load, β_min 100, factor 5 → I_B = 5 mA → R_B = (3.3 − 0.7)/5 mA ≈ 520 Ω → 470 Ω.

## CMOS logic

- Inverter: PMOS to V_DD, NMOS to ground. NAND: parallel PMOS, series NMOS. NOR: series PMOS, parallel NMOS. NAND is preferred over NOR because series PMOS (slower holes) hurts NOR more.
- Complex gates are naturally inverting (AOI, OAI). A static CMOS gate for function F has pull-down network implementing F' in NMOS.
- **Dynamic power** `P = α C V² f` (α = activity factor). **Static power** from leakage grows as thresholds drop.
- Propagation delay rises with load capacitance and falls with supply voltage.
- Fan-out: how many inputs one output can drive while meeting levels and timing.
- Never leave CMOS inputs floating: they draw shoot-through current and oscillate.

## Logic levels and interfacing

| Family | V_OH min | V_OL max | V_IH min | V_IL max |
|---|---|---|---|---|
| 5 V TTL | 2.4 | 0.4 | 2.0 | 0.8 |
| 5 V CMOS | 4.4 | 0.5 | 3.5 | 1.5 |
| 3.3 V LVCMOS | 2.4 | 0.4 | 2.0 | 0.8 |

(Typical values; check the datasheet.)

- Noise margin high = V_OH − V_IH, low = V_IL − V_OL.
- 3.3 V output → 5 V TTL input usually works (2.4 > 2.0). 3.3 V → 5 V CMOS input may not (needs 3.5 V). 5 V → 3.3 V input damages a non-5V-tolerant pin; use a divider, a level shifter, or a 5V-tolerant (FT) pin.
- Bidirectional open-drain lines (I2C) shift with a MOSFET-based shifter (BSS138 circuit) or a dedicated IC.

## Power and board-level practice

- One 100 nF ceramic decoupling capacitor per power pin, as close to the pin as possible, plus bulk capacitance (1–10 µF) per rail.
- Linear regulator dissipation = (V_in − V_out) × I_load. 12 V → 3.3 V at 200 mA wastes 1.74 W: use a buck converter.
- LDO dropout: V_in must exceed V_out by the dropout voltage.
- Keep ground returns short; a solid ground plane beats thin ground traces. Separate noisy (motor) and quiet (analog) return paths meeting at one point.
- Crystal load capacitors: `C_load = (C1 × C2)/(C1 + C2) + C_stray`; with C1 = C2, `C1 = 2 (C_load − C_stray)`.
- Signal integrity: when trace length exceeds about 1/6 of the rise-time distance, treat it as a transmission line and terminate it.

## Measurement tips

- Multimeter current mode goes in series; voltage in parallel. Never measure voltage in current mode.
- Scope ground clip connects to earth ground on mains-powered scopes: do not clip it to a non-ground node of a mains-referenced circuit.
- Use ×10 probes for fast edges; short ground springs to see real ringing.

## Common mistakes

- Using V_GS(th) as if it were the full-on gate voltage.
- Forgetting the flyback diode on an inductive load.
- Driving an LED or motor directly from a GPIO pin beyond its current rating.
- Ignoring the load when computing a voltage divider.
- Omitting decoupling capacitors and then chasing "random" resets.
