# Seal — Benchmark Results

*Generated 2026-07-29 04:19:07*  
Platform: `Windows-11-10.0.26200-SP0` · Python 3.14.2 · cryptography 49.0.0 · AMD64

---

## 1. AEAD Cipher Throughput

### AES-256-GCM

| Size | Encrypt (µs) | Decrypt (µs) | Enc MB/s | Dec MB/s |
|------|-------------|-------------|----------|----------|
| 64B | 3.5 | 3.2 | 17.4 | 19.1 |
| 256B | 3.4 | 3.1 | 71.8 | 78.8 |
| 1KB | 8.5 | 7.8 | 114.2 | 125.2 |
| 4KB | 4.6 | 4.2 | 849.2 | 930.1 |
| 64KB | 19.8 | 19.0 | 3156.6 | 3289.5 |
| 256KB | 71.9 | 71.3 | 3474.6 | 3506.3 |
| 1MB | 875.7 | 880.7 | 1142.0 | 1135.5 |

### ChaCha20-Poly1305

| Size | Encrypt (µs) | Decrypt (µs) | Enc MB/s | Dec MB/s |
|------|-------------|-------------|----------|----------|
| 64B | 3.4 | 3.1 | 18.0 | 19.7 |
| 256B | 3.5 | 3.3 | 69.8 | 74.0 |
| 1KB | 4.2 | 3.8 | 232.5 | 257.0 |
| 4KB | 5.8 | 5.5 | 673.5 | 710.2 |
| 64KB | 41.3 | 41.2 | 1513.3 | 1517.0 |
| 256KB | 155.7 | 156.4 | 1605.7 | 1598.5 |
| 1MB | 2615.8 | 2651.0 | 382.3 | 377.2 |

---

## 2. PBKDF2 Key Derivation (SHA-256, 600K iterations)

| Metric | Value |
|--------|-------|
| Median | 608.1 ms |
| Min | 542.3 ms |
| Max | 739.9 ms |

---

## 3. DEK Wrap / Unwrap (AES-GCM envelope)

| Metric | Value |
|--------|-------|
| Wrap median | 14.0 µs |
| Unwrap median | 15.2 µs |
| Total roundtrip | 29.2 µs |

---

## 4. Full Save → Load Roundtrip

| Metric | Value |
|--------|-------|
| Save median | 10.87 ms |
| Load median | 17.35 ms |
| Roundtrip median | 28.23 ms |
| Iterations | 100 |

---

## 5. Audit Log Append

| Metric | Value |
|--------|-------|
| Append median | 8220.1 µs |
| Append p99 | 25055.0 µs |
| Total entries | 1000 |

---

*All benchmarks use `time.perf_counter()`. Medians over stated iteration counts.*
