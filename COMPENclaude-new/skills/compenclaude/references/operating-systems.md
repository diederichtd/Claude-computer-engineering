# Operating systems

Processes, scheduling, synchronization, deadlock, memory, and file systems, with the methods for solving trace-style problems.

## Contents

- Processes and threads
- CPU scheduling
- Synchronization
- Deadlock
- Memory management
- File systems
- I/O
- Common mistakes

## Processes and threads

- Process: address space + resources + one or more threads. Thread: PC, registers, stack; shares the address space with sibling threads.
- States: new → ready ⇄ running → waiting → ready; running → terminated.
- Context switch saves/restores registers, switches page tables (process switch only), and pollutes caches and the TLB.
- System call: user mode traps into kernel mode (`ecall` on RISC-V, `syscall` on x86-64, `svc` on ARM).
- `fork()` returns 0 in the child and the child's PID in the parent; memory is copy-on-write. n sequential `fork()` calls in straight-line code produce 2^n processes. `exec()` replaces the image; `wait()` reaps a child (unreaped children are zombies).

## CPU scheduling

Metrics (per process):
- turnaround = completion − arrival
- waiting = turnaround − burst (for CPU-only jobs)
- response = first time on CPU − arrival

| Algorithm | Behavior | Notes |
|---|---|---|
| FCFS | run in arrival order | convoy effect |
| SJF (non-preemptive) | shortest next burst | optimal average waiting time; starvation |
| SRTF (preemptive SJF) | preempt when a shorter job arrives | optimal average waiting among preemptive |
| Round robin | time quantum q | large q → FCFS; small q → overhead; good response |
| Priority | highest priority first | starvation; fix with aging |
| MLFQ | multiple queues, demote CPU hogs | approximates SJF without knowing bursts |
| CFS (Linux) | pick task with least virtual runtime | red-black tree, weights from nice values |

Method for any scheduling question: draw the Gantt chart with times, then fill a table (arrival, burst, completion, turnaround, waiting). State the tie-breaking rule (usually lower PID/earlier arrival first) and, for RR, whether a newly arrived process enters the queue before the preempted one (convention: new arrival first).

## Synchronization

Critical-section requirements: mutual exclusion, progress, bounded waiting.

- **Mutex/lock**: one owner. Spinlocks for short waits on multiprocessors; sleeping locks otherwise.
- **Semaphore**: integer with `wait/P` (decrement, block if negative or zero) and `signal/V` (increment, wake one). Binary for mutual exclusion or signaling; counting for N resources.
- **Condition variable**: always used with a mutex; `wait` atomically releases the mutex and sleeps. **Always wait in a while loop.**
- **Monitor**: mutex + condition variables bundled with the data.
- Hardware support: test-and-set, compare-and-swap, LR/SC, fetch-and-add. Peterson's algorithm works only with sequential consistency (needs fences on modern CPUs).

Producer–consumer with a bounded buffer (pthreads):

```c
pthread_mutex_lock(&m);
while (count == N)                  // while, not if
    pthread_cond_wait(&not_full, &m);
buf[in] = item; in = (in + 1) % N; count++;
pthread_cond_signal(&not_empty);
pthread_mutex_unlock(&m);
```

Semaphore version: `empty = N`, `full = 0`, `mutex = 1`. Producer: `P(empty); P(mutex); put; V(mutex); V(full)`. Swapping the order `P(mutex); P(empty)` deadlocks when the buffer is full.

Classic problems: producer–consumer, readers–writers (reader or writer preference, starvation), dining philosophers (break circular wait: one philosopher picks up in reverse order, or limit to N − 1 at the table).

## Deadlock

Coffman conditions (all four needed): mutual exclusion, hold and wait, no preemption, circular wait.

- Prevention: break one condition (global lock ordering breaks circular wait; request all at once breaks hold-and-wait).
- Avoidance: **Banker's algorithm**. `Need = Max − Allocation`. Safe if some order lets every process finish: repeatedly find a process with `Need ≤ Work`, then `Work += Allocation`. Grant a request only if the resulting state is safe.
- Detection: wait-for graph cycle (single-instance resources) or the detection variant of Banker's; then recover by killing or preempting.

## Memory management

- Contiguous allocation: first-fit, best-fit, worst-fit; external fragmentation; compaction.
- Paging removes external fragmentation; internal fragmentation averages half a page per segment.
- Address translation arithmetic, multi-level tables, TLBs: see `computer-architecture.md` → Virtual memory (and `cecalc.py vm`).
- Effective access time with page faults: `EAT = (1 − p) × mem_time + p × fault_time`. With a fault time of 8 ms and memory 100 ns, p = 1/1000 makes EAT ≈ 8.1 µs (80× slower).

### Page replacement

Trace the reference string with a table of frames per step; count faults (initial loads count).

| Algorithm | Rule | Notes |
|---|---|---|
| FIFO | evict oldest loaded | **Belady's anomaly**: more frames can cause more faults |
| OPT | evict the page used farthest in the future | optimal; needs future knowledge; benchmark only |
| LRU | evict least recently used | stack algorithm, no Belady's anomaly |
| Clock (second chance) | circular scan, clear reference bits, evict first with bit 0 | practical LRU approximation |
| LFU / MFU | frequency-based | rarely good alone |

Thrashing: total working sets exceed physical memory; CPU utilization collapses. Fix with working-set or page-fault-frequency control, or by running fewer processes.

## File systems

- Inode holds metadata and block pointers; directory entries map names to inode numbers. Hard links share an inode; symlinks store a path.
- Max file size with 12 direct pointers, 1 single, 1 double, 1 triple indirect, block size B, pointer size P: `(12 + B/P + (B/P)^2 + (B/P)^3) × B`. With B = 4 KiB, P = 4 B: 1024 pointers per block → about 4 TiB.
- Allocation: contiguous, linked (FAT), indexed (inodes), extents.
- Journaling writes metadata (or data) to a log first, so a crash leaves a consistent state after replay.

## I/O

- Polling (busy-wait), interrupt-driven, DMA (device transfers blocks, interrupts on completion).
- Disk scheduling: FCFS, SSTF, SCAN (elevator), C-SCAN, LOOK/C-LOOK. Total head movement = Σ |track differences|. State the initial direction for SCAN/LOOK.
- Buffering, caching, spooling; SSDs need no seek scheduling but have erase-block and wear-leveling constraints.

## Common mistakes

- Using `if` instead of `while` around condition variable waits.
- Forgetting that `sem_wait` order matters (deadlock in bounded buffer).
- Counting the initial page loads as hits in replacement traces.
- Leaving the tie-breaking rule unstated in scheduling problems.
- Assuming `fork()` in a loop creates n processes instead of 2^n.
