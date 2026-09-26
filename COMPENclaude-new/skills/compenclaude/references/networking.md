# Networking

Layers, addressing, delay math, TCP, and error-detecting codes.

## Contents

- Layers
- Addressing and subnetting
- Delay and throughput
- TCP and UDP
- Link layer
- Error detection and correction
- Security basics
- Common mistakes

## Layers

| OSI | TCP/IP | Unit | Examples |
|---|---|---|---|
| 7 Application / 6 Presentation / 5 Session | Application | message | HTTP, DNS, TLS, SSH, MQTT |
| 4 Transport | Transport | segment (TCP) / datagram (UDP) | TCP, UDP, QUIC (over UDP) |
| 3 Network | Internet | packet | IPv4, IPv6, ICMP |
| 2 Data link | Link | frame | Ethernet, Wi-Fi (802.11), ARP |
| 1 Physical | Link | bits | cables, radio, encoding |

Encapsulation: each layer adds its header (Ethernet 14 B + 4 B FCS, IPv4 20 B min, TCP 20 B min, UDP 8 B). Ethernet MTU 1500 B → max TCP payload (MSS) 1460 B without options.

## Addressing and subnetting

- IPv4 = 32 bits. Prefix /n: n network bits, 32 − n host bits.
- Addresses per subnet 2^(32−n). Usable hosts = 2^(32−n) − 2 (network and broadcast reserved) for n ≤ 30; /31 = 2 (point-to-point links, RFC 3021); /32 = 1.
- Network address = IP AND mask. Broadcast = network OR NOT mask.
- Private ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16. Loopback 127.0.0.0/8. Link-local 169.254.0.0/16.
- VLSM: allocate the largest subnets first, each aligned to its own size.
- IPv6 = 128 bits; /64 per LAN; SLAAC; no broadcast (multicast instead).
- MAC address = 48 bits. ARP maps IPv4 → MAC on the local link. Routers forward by longest-prefix match.
- NAT maps private addresses and ports to a public address. DHCP assigns addresses (DORA: Discover, Offer, Request, Ack). DNS resolves names (UDP 53, TCP for large responses).

Calculator: `cecalc.py subnet 192.168.10.0/24 --split 26`, `cecalc.py subnet --hosts 50`.

## Delay and throughput

For a packet of L bits on a link of rate R bits/s, length d, propagation speed s:

- transmission delay = L / R
- propagation delay = d / s (s ≈ 2 × 10^8 m/s in fiber or copper)
- total per hop = processing + queuing + transmission + propagation
- store-and-forward over N links (N − 1 routers), one packet: N × L/R + total propagation
- bandwidth–delay product = R × RTT (bits in flight needed to fill the pipe)
- Stop-and-wait utilization = (L/R) / (L/R + RTT). Sliding window W packets: min(1, W × (L/R) / (L/R + RTT)).
- Throughput of a path = the bottleneck link rate.
- Units: 1 Mbps = 10^6 bits/s. 1 MB (file) is usually 10^6 or 2^20 bytes; state which. Multiply bytes by 8.

Worked example: 1500-byte packet, 100 Mbps link, 2000 km. Transmission = 12 000 / 10^8 = 120 µs. Propagation = 2×10^6 / 2×10^8 = 10 ms. Propagation dominates.

## TCP and UDP

- UDP: connectionless, no reliability, no ordering, 8-byte header. Good for DNS, streaming, games, QUIC.
- TCP: connection-oriented, reliable, ordered byte stream.
  - 3-way handshake: SYN → SYN-ACK → ACK. Teardown: FIN/ACK each direction; TIME_WAIT = 2 × MSL.
  - Sequence numbers count bytes; ACK = next expected byte.
  - **Flow control**: receiver-advertised window (don't overrun the receiver).
  - **Congestion control**: congestion window; slow start (cwnd doubles per RTT until ssthresh), congestion avoidance (+1 MSS per RTT), fast retransmit on 3 duplicate ACKs, fast recovery (Reno: cwnd halves). Timeout → cwnd back to 1 MSS (Tahoe/Reno). CUBIC and BBR are modern defaults.
  - Effective window = min(cwnd, rwnd). Throughput ≈ window / RTT.
- Ports: 0–1023 well-known (HTTP 80, HTTPS 443, SSH 22, DNS 53). A connection is identified by the 5-tuple.

## Link layer

- Ethernet: CSMA/CD in old half-duplex hubs; switched full-duplex today. Switches learn MAC → port tables. VLANs (802.1Q) split broadcast domains.
- Minimum Ethernet frame 64 bytes (so collisions were detectable in half-duplex).
- Wi-Fi uses CSMA/CA (collision avoidance, ACKs, RTS/CTS for hidden terminals).
- ALOHA efficiency: pure 1/(2e) ≈ 18.4%, slotted 1/e ≈ 36.8%.

## Error detection and correction

- Parity: detects any odd number of bit errors.
- Internet checksum: 16-bit ones' complement sum of 16-bit words, then complemented. Weak but cheap.
- **CRC**: append r zeros (r = degree of generator), divide mod 2 (XOR), append the remainder. Detects all burst errors of length ≤ r. Receiver divides the whole frame; remainder 0 means no detected error.
- **Hamming code**: r parity bits for m data bits need `2^r ≥ m + r + 1`. Parity bits sit at positions 1, 2, 4, 8, …; parity bit p covers positions whose index has bit p set. Syndrome = XOR of positions of all 1 bits (with even parity) = position of a single-bit error. SEC-DED adds one overall parity bit to detect (not correct) double errors.
- Hamming distance d: detects d − 1 errors, corrects ⌊(d − 1)/2⌋.

Calculator: `cecalc.py crc --data 11010011101100 --poly 1011`, `cecalc.py hamming 1011`, `cecalc.py hamming 0110111 --check`.

## Security basics

- Symmetric encryption (AES) for bulk data; asymmetric (RSA, ECC) for key exchange and signatures; hashes (SHA-256) for integrity; MACs (HMAC) for integrity + authenticity.
- TLS: handshake agrees on keys (ECDHE), authenticates the server by certificate, then encrypts with AES-GCM or ChaCha20-Poly1305.
- Firewalls filter by address, port, and connection state.

## Common mistakes

- Forgetting the two reserved addresses when counting hosts.
- Mixing bits and bytes in delay calculations.
- Confusing flow control (receiver) with congestion control (network).
- Treating latency and bandwidth as the same thing.
- Using the wrong generator degree when appending zeros for CRC.
