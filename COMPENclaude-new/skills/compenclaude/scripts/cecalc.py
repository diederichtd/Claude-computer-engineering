#!/usr/bin/env python3
"""cecalc: exact calculators for computer engineering problems.

Standard library only (Python 3.9+). Every command prints its working, so the
numbers can be checked by hand.

    python3 cecalc.py <command> -h      # options for one command

Commands
    conv     integer bases, two's complement, Gray code, byte order
    float    IEEE 754 encode/decode (single or double)
    cache    address breakdown + optional trace simulation (LRU/FIFO, 3C misses)
    amat     average memory access time, multi-level
    cpu      iron law: CPU time from IC, CPI (or instruction mix), clock
    amdahl   overall speedup, or speedup needed to hit a target
    vm       virtual memory: page offset/VPN bits, page-table size, levels, TLB reach
    subnet   IPv4/IPv6 subnet facts, splitting, prefix for N hosts
    timer    MCU timer prescaler/reload search for a target frequency
    baud     UART divisor and baud error
    adc      ADC LSB size and code <-> voltage
    rc       RC time constant, cutoff frequency, charge fraction
    hamming  Hamming(SEC) encode or check/correct
    crc      CRC remainder by mod-2 long division
"""
from __future__ import annotations

import argparse
import ipaddress
import math
import re
import struct
import sys
from collections import OrderedDict
from decimal import Decimal, InvalidOperation, getcontext

getcontext().prec = 80

# --------------------------------------------------------------------------- parsing

_SI = {"": 1.0, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3,
       "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}
_SI_RE = re.compile(
    r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([pnuµmkKMGT]?)\s*"
    r"(?i:hz|ohms?|Ω|f|s|v|a|bps|baud)?\s*$")
_SIZE_RE = re.compile(r"^\s*(\d+)\s*([kKmMgGtT]?)(?:i?[bB])?\s*$")


def die(msg: str) -> None:
    sys.exit(f"error: {msg}")


def parse_si(text: str) -> float:
    """'16MHz' -> 16e6, '100n' -> 1e-7, '4.7uF' -> 4.7e-6, '2e6' -> 2e6."""
    m = _SI_RE.match(text)
    if not m:
        die(f"cannot parse quantity {text!r} (try forms like 16MHz, 10k, 100n, 2e6)")
    return float(m.group(1)) * _SI[m.group(2)]


def parse_size(text: str) -> int:
    """Byte sizes are binary: '32KiB', '32KB' and '32K' all mean 32768."""
    m = _SIZE_RE.match(text)
    if not m:
        return parse_int(text)
    return int(m.group(1)) * 1024 ** "_KMGT".index(m.group(2).upper() or "_")


def parse_int(text: str) -> int:
    t = text.strip().replace("_", "")
    try:
        return int(t, 0)
    except ValueError:
        try:
            return int(t, 10)
        except ValueError:
            die(f"cannot parse integer {text!r} (use 42, -7, 0x2A, 0b101010, 0o52)")
    raise AssertionError


def ilog2(n: int, what: str) -> int:
    if n <= 0 or n & (n - 1):
        die(f"{what} must be a power of two (got {n})")
    return n.bit_length() - 1


# --------------------------------------------------------------------------- formatting

def eng(x: float, unit: str = "") -> str:
    if x == 0 or math.isinf(x) or math.isnan(x):
        return f"{x:g} {unit}".strip()
    for exp, p in ((12, "T"), (9, "G"), (6, "M"), (3, "k"), (0, ""),
                   (-3, "m"), (-6, "µ"), (-9, "n"), (-12, "p")):
        if abs(x) >= 10 ** exp:
            return f"{x / 10 ** exp:.6g} {p}{unit}".strip()
    return f"{x:.6g} {unit}".strip()


def human_bytes(n: int) -> str:
    for p, unit in ((4, "TiB"), (3, "GiB"), (2, "MiB"), (1, "KiB")):
        if n >= 1024 ** p and n % 1024 ** p == 0:
            return f"{n // 1024 ** p} {unit} ({n} B)"
    return f"{n} B"


def grouped_bin(v: int, bits: int) -> str:
    s = format(v, f"0{bits}b")
    head = len(s) % 4
    parts = ([s[:head]] if head else []) + [s[i:i + 4] for i in range(head, len(s), 4)]
    return "_".join(parts)


def row(label: str, value) -> None:
    print(f"  {label:<24}{value}")


# --------------------------------------------------------------------------- conv

def cmd_conv(a) -> None:
    v = parse_int(a.value)
    bits = a.bits
    if bits is None:
        for bits in (8, 16, 32, 64, 128, 256):
            if (v >= 0 and v < 1 << bits) or (v < 0 and v >= -(1 << (bits - 1))):
                break
    if bits <= 0:
        die("--bits must be positive")
    if v < 0:
        if v < -(1 << (bits - 1)):
            die(f"{v} does not fit in {bits}-bit two's complement "
                f"(range {-(1 << (bits - 1))} .. {(1 << (bits - 1)) - 1})")
    elif v >= 1 << bits:
        die(f"{v} does not fit in {bits} bits (max unsigned {(1 << bits) - 1})")
    pattern = v & ((1 << bits) - 1)
    signed = pattern - (1 << bits) if pattern >> (bits - 1) else pattern
    hexw = (bits + 3) // 4

    print(f"{a.value} as a {bits}-bit pattern")
    row("hex", f"0x{pattern:0{hexw}X}")
    row("binary", grouped_bin(pattern, bits))
    row("octal", f"0o{pattern:o}")
    row("unsigned", pattern)
    row("signed (two's compl.)", signed)
    row("unsigned range", f"0 .. {(1 << bits) - 1}")
    row("signed range", f"{-(1 << (bits - 1))} .. {(1 << (bits - 1)) - 1}")
    row("Gray code (b ^ b>>1)", grouped_bin(pattern ^ (pattern >> 1), bits))
    row("popcount", bin(pattern).count("1"))
    if bits % 8 == 0:
        be = pattern.to_bytes(bits // 8, "big")
        row("memory, big-endian", " ".join(f"{b:02X}" for b in be))
        row("memory, little-endian", " ".join(f"{b:02X}" for b in reversed(be)))
    if v >= 0 and signed < 0:
        print(f"  note: MSB is set, so the same bits read as {signed} when signed.")


# --------------------------------------------------------------------------- float

_FMT = {32: (">f", ">I", 8, 23, 127), 64: (">d", ">Q", 11, 52, 1023)}


def cmd_float(a) -> None:
    note = None
    if a.hex:
        raw = parse_int(a.value)
        digits = len(a.value.lower().replace("0x", "").replace("_", ""))
        width = 64 if a.double or digits > 8 else 32
        if raw >> width:
            die(f"pattern does not fit in {width} bits")
        ffmt, ifmt, eb, mb, bias = _FMT[width]
        stored = struct.unpack(ffmt, struct.pack(ifmt, raw))[0]
    else:
        width = 64 if a.double else 32
        ffmt, ifmt, eb, mb, bias = _FMT[width]
        try:
            x = float(a.value)
        except ValueError:
            die(f"cannot parse float {a.value!r}")
        try:
            raw = struct.unpack(ifmt, struct.pack(ffmt, x))[0]
        except OverflowError:
            raw = ((1 if x < 0 else 0) << (eb + mb)) | (((1 << eb) - 1) << mb)
            note = "magnitude exceeds the largest finite value: rounds to infinity"
        stored = struct.unpack(ffmt, struct.pack(ifmt, raw))[0]

    sign = raw >> (eb + mb)
    exp = (raw >> mb) & ((1 << eb) - 1)
    frac = raw & ((1 << mb) - 1)
    name = "single (binary32)" if width == 32 else "double (binary64)"
    print(f"IEEE 754 {name}: 1 sign, {eb} exponent (bias {bias}), {mb} fraction bits")
    row("hex", f"0x{raw:0{width // 4}X}")
    row("fields s|exp|frac", f"{sign} | {exp:0{eb}b} | {frac:0{mb}b}")

    if exp == (1 << eb) - 1:
        row("class", "NaN" if frac else ("-inf" if sign else "+inf"))
    elif exp == 0 and frac == 0:
        row("class", "-0" if sign else "+0")
    else:
        if exp == 0:
            e, lead, cls = 1 - bias, "0", "subnormal"
        else:
            e, lead, cls = exp - bias, "1", "normal"
        row("class", cls)
        row("exponent", f"stored {exp}, unbiased {e}")
        mant = f"{frac:0{mb}b}".rstrip("0") or "0"
        row("value", f"{'-' if sign else '+'}{lead}.{mant} (binary) x 2^{e}")
        exact = f"{Decimal(stored):f}"
        if "." in exact:
            exact = exact.rstrip("0").rstrip(".")
        row("exact stored value", exact if abs(e) < 60 else f"{Decimal(stored):E}")
        row("shortest repr", repr(stored))
        row("ULP at this value", f"2^{e - mb} = {2.0 ** (e - mb):.6g}")
        if not a.hex:
            try:
                err = Decimal(a.value) - Decimal(stored)
                row("rounding error", "0 (exact)" if err == 0 else f"{err:.6E}")
            except InvalidOperation:
                pass
    if note:
        print(f"  note: {note}")


# --------------------------------------------------------------------------- cache

def _read_trace(a) -> list[int]:
    addrs = [parse_int(t) for t in (a.trace or [])]
    if a.trace_file:
        with open(a.trace_file) as fh:
            for line in fh:
                tokens = line.split("#")[0].split()
                if tokens:
                    addrs.append(parse_int(tokens[-1]))  # tolerate "R 0x1f" / "W 0x20"
    return addrs


def cmd_cache(a) -> None:
    size, block = parse_size(a.size), parse_size(a.block)
    if size % block:
        die("cache size must be a multiple of block size")
    lines = size // block
    ways = lines if str(a.assoc).lower() in ("full", "fa") else parse_int(a.assoc)
    if ways < 1 or lines % ways:
        die(f"associativity {ways} does not divide {lines} lines")
    sets = lines // ways
    ob, ib = ilog2(block, "block size"), ilog2(sets, "number of sets")
    tb = a.addr_bits - ib - ob
    if tb <= 0:
        die("address too short for this geometry")

    kind = "direct-mapped" if ways == 1 else ("fully associative" if sets == 1 else f"{ways}-way set associative")
    print(f"{human_bytes(size)} {kind}, {block} B blocks, {a.addr_bits}-bit byte addresses")
    row("lines (blocks)", lines)
    row("sets x ways", f"{sets} x {ways}")
    row("offset bits", f"{ob}   addr[{ob - 1}:0]" if ob else "0")
    row("index bits", f"{ib}   addr[{ib + ob - 1}:{ob}]" if ib else "0   (fully associative)")
    row("tag bits", f"{tb}   addr[{a.addr_bits - 1}:{ib + ob}]")
    meta = tb + 1 + (1 if a.write_back else 0)
    row("metadata per line", f"{tb} tag + 1 valid" + (" + 1 dirty" if a.write_back else "")
        + f" = {meta} bits")
    row("total storage", f"{size * 8} data + {lines * meta} metadata = {size * 8 + lines * meta} bits")

    addrs = _read_trace(a)
    if not addrs:
        return

    print(f"\nTrace ({a.policy.upper()} replacement, allocate on every miss)")
    print(f"  {'#':>3}  {'address':>12}  {'tag':>10}  {'set':>5}  {'off':>4}  result  {'evicted tag':>11}  miss type")
    cache = [OrderedDict() for _ in range(sets)]
    shadow: OrderedDict[int, None] = OrderedDict()  # fully-assoc LRU, same capacity
    seen: set[int] = set()
    counts = {"hit": 0, "compulsory": 0, "capacity": 0, "conflict": 0}
    for n, addr in enumerate(addrs, 1):
        blk = addr >> ob
        off, idx, tag = addr & (block - 1), blk & (sets - 1), blk >> ib
        s = cache[idx]
        shadow_hit = blk in shadow
        if shadow_hit:
            shadow.move_to_end(blk)
        else:
            if len(shadow) == lines:
                shadow.popitem(last=False)
            shadow[blk] = None
        evicted = ""
        if tag in s:
            result, mtype = "hit ", ""
            counts["hit"] += 1
            if a.policy == "lru":
                s.move_to_end(tag)
        else:
            result = "MISS"
            mtype = "compulsory" if blk not in seen else ("conflict" if shadow_hit else "capacity")
            counts[mtype] += 1
            if len(s) == ways:
                evicted = f"0x{s.popitem(last=False)[0]:X}"
            s[tag] = None
        seen.add(blk)
        print(f"  {n:>3}  {'0x%X' % addr:>12}  {'0x%X' % tag:>10}  {idx:>5}  {off:>4}  {result}    {evicted:>11}  {mtype}")
    total = len(addrs)
    misses = total - counts["hit"]
    print(f"\n  hits {counts['hit']}/{total} ({counts['hit'] / total:.2%}), misses {misses} "
          f"(compulsory {counts['compulsory']}, capacity {counts['capacity']}, conflict {counts['conflict']})")


# --------------------------------------------------------------------------- amat / cpu / amdahl

def cmd_amat(a) -> None:
    levels = []
    for spec in a.levels:
        try:
            hit, mr = spec.split(":")
            levels.append((float(hit), float(mr)))
        except ValueError:
            die(f"level {spec!r} must look like HIT_TIME:LOCAL_MISS_RATE, e.g. 1:0.05")
    penalty = a.mem
    terms = []
    for i in range(len(levels) - 1, -1, -1):
        hit, mr = levels[i]
        terms.append(f"L{i + 1}: {hit:g} + {mr:g} x {penalty:g} = {hit + mr * penalty:g}")
        penalty = hit + mr * penalty
    print("AMAT = hit time + local miss rate x miss penalty (innermost first)")
    for t in reversed(terms):
        row("", t)
    row("AMAT", f"{penalty:g} (same unit as inputs)")
    g = 1.0
    for i, (_, mr) in enumerate(levels):
        g *= mr
        row(f"global miss rate L{i + 1}", f"{g:.6g}")


def cmd_cpu(a) -> None:
    ic = parse_si(a.ic)
    if a.mix:
        cpi, parts = 0.0, []
        total_frac = 0.0
        for spec in a.mix.split(","):
            f, c = (float(x) for x in spec.split(":"))
            total_frac += f
            cpi += f * c
            parts.append(f"{f:g}x{c:g}")
        print(f"CPI = {' + '.join(parts)} = {cpi:g}")
        if abs(total_frac - 1) > 1e-9:
            print(f"  warning: fractions sum to {total_frac:g}, not 1")
    elif a.cpi is not None:
        cpi = a.cpi
    else:
        die("give --cpi or --mix")
    if a.clock:
        f = parse_si(a.clock)
    elif a.period:
        f = 1 / parse_si(a.period)
    else:
        die("give --clock or --period")
    t = ic * cpi / f
    print("CPU time = IC x CPI / f")
    row("instruction count", f"{ic:g}")
    row("CPI / IPC", f"{cpi:g} / {1 / cpi:.6g}")
    row("clock", f"{eng(f, 'Hz')} (period {eng(1 / f, 's')})")
    row("cycles", f"{ic * cpi:g}")
    row("CPU time", eng(t, "s"))
    row("native MIPS", f"{f / (cpi * 1e6):.6g}")


def cmd_amdahl(a) -> None:
    p = a.fraction
    if not 0 <= p <= 1:
        die("--fraction must be between 0 and 1")
    print("Speedup = 1 / ((1 - p) + p / s)")
    row("limit (s -> inf)", "inf" if p == 1 else f"{1 / (1 - p):.6g}x")
    if a.speedup is not None:
        s = a.speedup
        overall = 1 / ((1 - p) + (0 if math.isinf(s) else p / s))
        row(f"overall at s={s:g}", f"{overall:.6g}x")
    if a.target is not None:
        denom = 1 / a.target - (1 - p)
        if denom <= 0:
            row(f"s for {a.target:g}x", "impossible: target exceeds the limit")
        else:
            row(f"s for {a.target:g}x", f"{p / denom:.6g}x on the improved fraction")


# --------------------------------------------------------------------------- vm

def cmd_vm(a) -> None:
    page = parse_size(a.page)
    ob = ilog2(page, "page size")
    vpn = a.va_bits - ob
    print(f"{a.va_bits}-bit virtual addresses, {human_bytes(page)} pages, {a.pte}-byte PTEs")
    row("page offset bits", ob)
    row("VPN bits", vpn)
    row("flat table", f"2^{vpn} entries x {a.pte} B = {human_bytes((1 << vpn) * a.pte)}")
    if a.pa_bits:
        row("PFN bits", a.pa_bits - ob)
        row("physical pages", f"2^{a.pa_bits - ob}")
    per = page // a.pte
    bpl = ilog2(per, "PTEs per page")
    levels = math.ceil(vpn / bpl)
    row("PTEs per page", f"{per}  ({bpl} VPN bits per level)")
    row("levels (table = 1 page)", f"{levels}  split " +
        "+".join(str(min(bpl, vpn - bpl * i)) for i in reversed(range(levels))) + f" + {ob} offset")
    if a.tlb:
        row("TLB reach", human_bytes(a.tlb * page))


# --------------------------------------------------------------------------- subnet

def cmd_subnet(a) -> None:
    if a.hosts is not None:
        need = a.hosts + 2
        prefix = 32 - math.ceil(math.log2(need)) if a.hosts > 2 else (31 if a.hosts == 2 else 32)
        print(f"{a.hosts} hosts need /{prefix} "
              f"({2 ** (32 - prefix)} addresses, {max(2 ** (32 - prefix) - 2, a.hosts)} usable)")
        if not a.cidr:
            return
    if not a.cidr:
        die("give a CIDR block (e.g. 192.168.1.0/26) or --hosts N")
    try:
        net = ipaddress.ip_network(a.cidr, strict=False)
    except ValueError as e:
        die(str(e))
    print(str(net) + (f"   (normalized from {a.cidr})" if str(net) != a.cidr else ""))
    row("netmask", net.netmask)
    if net.version == 4:
        row("wildcard", net.hostmask)
    row("network", net.network_address)
    if net.version == 4:
        row("broadcast", net.broadcast_address)
    total = net.num_addresses
    if net.version == 4 and net.prefixlen <= 30:
        usable, first, last = total - 2, net.network_address + 1, net.broadcast_address - 1
    else:
        usable, first, last = total, net.network_address, net.broadcast_address
    row("total addresses", total)
    row("usable hosts", usable)
    row("host range", f"{first} - {last}")
    row("private (RFC1918 etc.)", net.is_private)
    if a.split:
        if a.split <= net.prefixlen:
            die("--split prefix must be longer than the network prefix")
        subs = list(net.subnets(new_prefix=a.split))
        print(f"\n  {len(subs)} subnets of /{a.split}:")
        for s in subs[:64]:
            print(f"    {s}")
        if len(subs) > 64:
            print(f"    ... {len(subs) - 64} more")


# --------------------------------------------------------------------------- embedded

def cmd_timer(a) -> None:
    clk = parse_si(a.clock)
    target = 1 / parse_si(a.period) if a.period else parse_si(a.target)
    prescalers = [int(x) for x in a.prescalers.split(",")]
    top = 1 << a.bits
    print(f"f_clk {eng(clk, 'Hz')}, target {eng(target, 'Hz')} ({eng(1 / target, 's')}), {a.bits}-bit counter")
    print("  counts = f_clk / (prescaler x f_target); counter runs 0..reload, so reload = counts - 1")
    print(f"  {'prescaler':>9}  {'counts':>10}  {'reload':>8}  {'actual':>14}  {'error':>9}")
    best = None
    for p in prescalers:
        exact = clk / (p * target)
        n = round(exact)
        if n < 1 or n > top:
            print(f"  {p:>9}  {exact:>10.2f}  {'out of range':>8}")
            continue
        actual = clk / (p * n)
        err = (actual - target) / target
        print(f"  {p:>9}  {n:>10}  {n - 1:>8}  {eng(actual, 'Hz'):>14}  {err:>+9.4%}")
        if best is None or abs(err) < abs(best[1]) - 1e-15:
            best = (p, err, n)
    if best:
        print(f"\n  best: prescaler {best[0]}, reload {best[2] - 1} "
              f"(STM32: PSC={best[0] - 1}, ARR={best[2] - 1}; AVR CTC: OCRnA={best[2] - 1})")
    else:
        print("\n  no prescaler reaches the target; use a wider timer or a larger prescaler")


def cmd_baud(a) -> None:
    clk, baud, os_ = parse_si(a.clock), parse_si(a.baud), a.oversample
    exact = clk / (os_ * baud)
    n = max(1, round(exact))
    actual = clk / (os_ * n)
    err = (actual - baud) / baud
    print(f"f_clk {eng(clk, 'Hz')}, target {baud:g} baud, oversampling x{os_}")
    row("divisor", f"{exact:.4f} -> {n}")
    row("actual baud", f"{actual:.2f}")
    row("error", f"{err:+.3%}" + ("   WARNING: above 2%, link may be unreliable" if abs(err) > 0.02 else ""))
    row("AVR UBRR (U2X=0)", n - 1 if os_ == 16 else "n/a (use --oversample 16)")
    if os_ == 8:
        row("AVR UBRR (U2X=1)", n - 1)
    row("STM32 BRR (OVER8=0)", f"{round(clk / baud)}  (fractional divider, error "
        f"{(clk / round(clk / baud) - baud) / baud:+.3%})")


def cmd_adc(a) -> None:
    vref = parse_si(a.vref)
    levels = 1 << a.bits
    lsb = vref / levels
    print(f"{a.bits}-bit ADC, Vref {eng(vref, 'V')}")
    row("codes", f"0 .. {levels - 1}")
    row("LSB = Vref / 2^N", eng(lsb, "V"))
    row("alt. Vref / (2^N - 1)", eng(vref / (levels - 1), "V") + "  (some datasheets)")
    if a.code is not None:
        c = parse_int(a.code)
        if not 0 <= c < levels:
            die(f"code must be 0..{levels - 1}")
        row(f"code {c} ->", f"{eng(c * lsb, 'V')} (bin low edge), {eng((c + 0.5) * lsb, 'V')} (bin centre)")
    if a.volts is not None:
        v = parse_si(a.volts)
        c = min(levels - 1, max(0, math.floor(v / lsb)))
        row(f"{eng(v, 'V')} ->", f"code {c} (0x{c:X})")
    row("quantization error", f"±{eng(lsb / 2, 'V')} (ideal, rounding ADC)")
    row("ideal SNR", f"{6.02 * a.bits + 1.76:.2f} dB (full-scale sine)")


def cmd_rc(a) -> None:
    r, c = parse_si(a.r), parse_si(a.c)
    tau = r * c
    print(f"R = {eng(r, 'Ω')}, C = {eng(c, 'F')}")
    row("tau = RC", eng(tau, "s"))
    row("-3 dB cutoff 1/(2πRC)", eng(1 / (2 * math.pi * tau), "Hz"))
    row("10-90% rise (2.2 tau)", eng(2.2 * tau, "s"))
    row("settle to 99.3% (5 tau)", eng(5 * tau, "s"))
    if a.t:
        t = parse_si(a.t)
        frac = 1 - math.exp(-t / tau)
        row(f"charge after {eng(t, 's')}", f"{frac:.4%} of final value")


# --------------------------------------------------------------------------- coding

def _bits(text: str, what: str) -> list[int]:
    t = text.replace("_", "").replace(" ", "")
    if not t or set(t) - {"0", "1"}:
        die(f"{what} must be a string of 0s and 1s")
    return [int(ch) for ch in t]


def cmd_hamming(a) -> None:
    if a.check:
        code = _bits(a.value, "codeword")
        n = len(code)
        syndrome = 0
        for pos in range(1, n + 1):
            if code[pos - 1]:
                syndrome ^= pos
        print(f"Hamming check of {a.value} (positions 1..{n}, left to right, even parity)")
        row("syndrome", f"{syndrome} (0b{syndrome:b})")
        if syndrome == 0:
            row("result", "no single-bit error detected")
        elif syndrome > n:
            row("result", "syndrome points past the word: multi-bit error")
        else:
            code[syndrome - 1] ^= 1
            row("result", f"bit {syndrome} flipped; corrected {''.join(map(str, code))}")
        data = [code[p - 1] for p in range(1, n + 1) if p & (p - 1)]
        row("data bits", "".join(map(str, data)))
        print("  note: a single syndrome cannot tell a 2-bit error from a 1-bit one; use SEC-DED for that.")
        return
    data = _bits(a.value, "data")
    m = len(data)
    r = 0
    while (1 << r) < m + r + 1:
        r += 1
    n = m + r
    code = [0] * (n + 1)  # 1-indexed
    it = iter(data)
    for pos in range(1, n + 1):
        if pos & (pos - 1):
            code[pos] = next(it)
    print(f"Hamming({n},{m}) encode of {a.value}: parity at positions 1,2,4,...; even parity")
    for i in range(r):
        p = 1 << i
        covered = [q for q in range(1, n + 1) if q & p and q != p]
        code[p] = sum(code[q] for q in covered) % 2
        row(f"p{p}", f"XOR of positions {covered} = {code[p]}")
    row("codeword (pos 1..n)", "".join(map(str, code[1:])))


def cmd_crc(a) -> None:
    data, poly = _bits(a.data, "data"), _bits(a.poly, "generator")
    if poly[0] != 1:
        die("generator must start with 1")
    deg = len(poly) - 1
    work = data + [0] * deg
    print(f"CRC: data {a.data}, generator {a.poly} (degree {deg}); append {deg} zeros and divide mod 2")
    for i in range(len(data)):
        if work[i]:
            for j in range(len(poly)):
                work[i + j] ^= poly[j]
    rem = work[-deg:] if deg else []
    row("remainder", "".join(map(str, rem)) or "(none)")
    row("transmitted", "".join(map(str, data + rem)))


# --------------------------------------------------------------------------- CLI

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("conv", help="integer bases / two's complement")
    p.add_argument("value", help="42, -7, 0x2A, 0b101010, 0o52")
    p.add_argument("--bits", type=int, help="bit width (default: smallest of 8/16/32/64 that fits)")
    p.set_defaults(fn=cmd_conv)

    p = sp.add_parser("float", help="IEEE 754 encode/decode")
    p.add_argument("value", help="decimal number, or a bit pattern with --hex")
    p.add_argument("--hex", action="store_true", help="decode VALUE as a raw bit pattern")
    p.add_argument("--double", action="store_true", help="use binary64")
    p.set_defaults(fn=cmd_float)

    p = sp.add_parser("cache", help="cache geometry and trace simulation")
    p.add_argument("--size", required=True, help="data capacity, e.g. 32KiB")
    p.add_argument("--block", required=True, help="block/line size in bytes, e.g. 64")
    p.add_argument("--assoc", default="1", help="ways (1 = direct-mapped) or 'full'")
    p.add_argument("--addr-bits", type=int, default=32)
    p.add_argument("--write-back", action="store_true", help="count a dirty bit per line")
    p.add_argument("--policy", choices=["lru", "fifo"], default="lru")
    p.add_argument("--trace", nargs="*", help="byte addresses to simulate")
    p.add_argument("--trace-file", help="file with one address per line (last token used)")
    p.set_defaults(fn=cmd_cache)

    p = sp.add_parser("amat", help="average memory access time")
    p.add_argument("--levels", nargs="+", required=True, help="HIT:LOCAL_MISS_RATE per level, L1 first")
    p.add_argument("--mem", type=float, required=True, help="main-memory access time")
    p.set_defaults(fn=cmd_amat)

    p = sp.add_parser("cpu", help="iron law of performance")
    p.add_argument("--ic", required=True, help="instruction count, e.g. 2e9 or 2G")
    p.add_argument("--cpi", type=float)
    p.add_argument("--mix", help="FRACTION:CPI pairs, e.g. 0.5:1,0.3:2,0.2:5")
    p.add_argument("--clock", help="e.g. 3GHz")
    p.add_argument("--period", help="e.g. 250ps")
    p.set_defaults(fn=cmd_cpu)

    p = sp.add_parser("amdahl", help="Amdahl's law")
    p.add_argument("--fraction", type=float, required=True, help="fraction of time that is improved")
    p.add_argument("--speedup", type=float, help="speedup of that fraction (inf allowed)")
    p.add_argument("--target", type=float, help="solve for the speedup needed to reach this overall")
    p.set_defaults(fn=cmd_amdahl)

    p = sp.add_parser("vm", help="paging arithmetic")
    p.add_argument("--va-bits", type=int, required=True)
    p.add_argument("--page", required=True, help="page size, e.g. 4KiB")
    p.add_argument("--pte", type=int, default=8, help="bytes per page-table entry")
    p.add_argument("--pa-bits", type=int)
    p.add_argument("--tlb", type=int, help="TLB entries, for reach")
    p.set_defaults(fn=cmd_vm)

    p = sp.add_parser("subnet", help="IP subnetting")
    p.add_argument("cidr", nargs="?", help="e.g. 10.0.0.0/22")
    p.add_argument("--split", type=int, help="list subnets of this longer prefix")
    p.add_argument("--hosts", type=int, help="smallest IPv4 prefix holding N hosts")
    p.set_defaults(fn=cmd_subnet)

    p = sp.add_parser("timer", help="MCU timer prescaler/reload")
    p.add_argument("--clock", required=True, help="timer input clock, e.g. 16MHz")
    p.add_argument("--target", help="interrupt/overflow frequency, e.g. 1kHz")
    p.add_argument("--period", help="or the period, e.g. 10ms")
    p.add_argument("--bits", type=int, default=16)
    p.add_argument("--prescalers", default="1,8,64,256,1024", help="comma list")
    p.set_defaults(fn=cmd_timer)

    p = sp.add_parser("baud", help="UART divisor and error")
    p.add_argument("--clock", required=True)
    p.add_argument("--baud", required=True)
    p.add_argument("--oversample", type=int, default=16)
    p.set_defaults(fn=cmd_baud)

    p = sp.add_parser("adc", help="ADC resolution and conversion")
    p.add_argument("--bits", type=int, required=True)
    p.add_argument("--vref", required=True, help="e.g. 3.3V")
    p.add_argument("--code", help="convert a code to volts")
    p.add_argument("--volts", help="convert a voltage to a code")
    p.set_defaults(fn=cmd_adc)

    p = sp.add_parser("rc", help="RC circuit timing")
    p.add_argument("--r", required=True, help="e.g. 10k")
    p.add_argument("--c", required=True, help="e.g. 100nF")
    p.add_argument("--t", help="elapsed time for charge fraction, e.g. 1ms")
    p.set_defaults(fn=cmd_rc)

    p = sp.add_parser("hamming", help="Hamming code encode/check")
    p.add_argument("value", help="data bits (encode) or codeword (with --check)")
    p.add_argument("--check", action="store_true")
    p.set_defaults(fn=cmd_hamming)

    p = sp.add_parser("crc", help="CRC by polynomial long division")
    p.add_argument("--data", required=True, help="message bits, e.g. 11010011101100")
    p.add_argument("--poly", required=True, help="generator bits, e.g. 1011 for x^3+x+1")
    p.set_defaults(fn=cmd_crc)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
