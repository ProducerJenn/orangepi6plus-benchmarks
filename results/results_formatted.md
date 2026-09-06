# Ollama Benchmark Results - Orange Pi 6 Plus

## System Info

| Property | Value |
|----------|-------|
| CPU Model | CIX P1 CD8160 (Cortex-A720/A520) |
| CPU Count | 12 |
| RAM | 14.9 GB |
| Ollama Version | 0.31.2 |

---

## Model Comparison (8 threads, ctx 2048, warm)

| Model | Size | Max ctx | RAM @2K | Prefill (tok/s) | Gen (tok/s) | TTFT (ms) |
|---|---|---:|---:|---:|---:|---:|
| lfm2.5-350m | 379 MB | 128K | 510 MB | 739.57 | 76.47 | 253 |
| tiny-agent-a 0.5b | 531 MB | 32K | 760 MB | 532.65 | 54.10 | 479 |
| qwen2.5:1.5b | 986 MB | 32K | 1.4 GB | 304.80 | 28.57 | 615 |
| qwen3.5:0.8b | 1.0 GB | 262K | 1.4 GB | 254.58 | 31.27 | 919 |
| lfm2.5-1.2b | 730 MB | 128K | 929 MB | 233.24 | 39.23 | 468 |
| **LFM2.5-8B-A1B (Q4_K_M)** | **5.2 GB** | **128K** | **5.4 GB** | **88.56** | **24.62** | **804** |
| lfm2.5-8b-a1b (old) | 5.2 GB | 128K | 5.4 GB | 88.80 | 24.50 | 850 |
| phi4-mini-reasoning | 3.2 GB | 128K | 4.3 GB | 126.15 | 11.10 | 1029 |
| phi4-mini | 2.5 GB | 128K | 3.6 GB | 77.23 | 13.05 | 839 |
| gemma3:4b | 3.3 GB | 128K | 3.6 GB | 73.24 | 13.10 | 1260 |
| qwen2.5:7b | 4.7 GB | 32K | 5.1 GB | 71.73 | 8.16 | 1228 |
| qwen3.5:4b | 3.4 GB | 262K | 3.7 GB | 57.21 | 11.67 | 1327 |
| qwen3:latest (official 8B) | 5.2 GB | 40K | 5.9 GB | 39.55 | 7.27 | 1182 |
| qwen3-8b-unsloth UD-Q4_K_XL (instruct) | 5.1 GB | 40K | 5.8 GB | 30.50 | 7.34 | 1466 |
| qwen3-8b-unsloth UD-Q4_K_XL (thinking) | 5.1 GB | 40K | 5.8 GB | 30.23 | 7.31 | 1317 |

RAM @2K = resident memory at 2048 ctx from `ollama ps` (weights + KV cache). Max ctx = native ceiling from GGUF metadata; test ran at 2048.

---

## Thread Scaling Test (qwen2.5:1.5b)

| Threads | Prefill (tok/s) | Gen (tok/s) |
|--------:|---:|---:|
| 1 | 29.59 | 10.30 |
| 2 | 55.77 | 16.73 |
| 4 | 107.15 | 24.44 |
| 6 | 147.88 | 28.07 |
| 8 | 182.08 | 29.00 |
| 12 | 93.11 | 12.50 |

---

## Key Findings (8 threads, warm model)

1. **LFM2.5-8B-A1B dominates the big models**: 24.6 tok/s gen, 88.6 tok/s prefill, 804 ms TTFT
2. **Qwen3-8B TTFT is 1.7x slower** than LFM2.5-8B-A1B (1.3s vs 804ms) and gen is 3.4x slower
3. **Small denses (<1B) are fast for tiny tasks**: lfm2.5-350m at 76.5 tok/s gen with 253ms TTFT
4. **8 threads is the sweet spot** for 4B+ models on this CPU
5. **Model size / speed is roughly proportional** — MoE beats dense at the same parameter count

---

## Higher-Context Comparison (8 threads)

| Model | ctx | RAM | Prefill (tok/s) | Gen (tok/s) | TTFT (ms) |
|---|---|---:|---:|---:|---:|
| LiquidAI/lfm2.5-1.2b | 2048 | 929 MB | 233.24 | 39.23 | 468 |
| LiquidAI/lfm2.5-1.2b | 16384 | 1.2 GB | 235.08 | 39.79 | 431 |
| LFM2.5-8B-A1B (Q4_K_M) | 2048 | 5.4 GB | 88.56 | 24.62 | 804 |
| LFM2.5-8B-A1B (Q4_K_M) | 16384 | 5.5 GB | 88.32 | 24.51 | 951 |
| phi4-mini | 2048 | 3.6 GB | 77.23 | 13.05 | 839 |
| phi4-mini | 8192 | 5.3 GB | 78.22 | 13.59 | 869 |
| gemma3:4b | 2048 | 3.6 GB | 73.24 | 13.10 | 1260 |
| gemma3:4b | 16384 | 3.9 GB | 68.73 | 13.00 | 1335 |
| qwen2.5:7b | 2048 | 5.1 GB | 71.73 | 8.16 | 1228 |
| qwen2.5:7b | 16384 | 6.9 GB | 71.15 | 8.05 | 1209 |
| qwen3.5:4b | 2048 | 3.7 GB | 57.21 | 11.67 | 1327 |
| qwen3.5:4b | 16384 | 4.2 GB | 56.18 | 11.47 | 1325 |
| qwen3:latest (official 8B) | 2048 | 5.9 GB | 39.55 | 7.27 | 1182 |
| qwen3:latest (official 8B) | 16384 | 10 GB | 39.46 | 7.37 | 1197 |
| qwen3-8b-unsloth (instruct) | 2048 | 5.8 GB | 30.50 | 7.34 | 1466 |
| qwen3-8b-unsloth (instruct) | 16384 | 10 GB | 30.48 | 7.43 | 1496 |

Key: context size costs RAM, not throughput (gen/prefill within noise between 2K and 16K).
