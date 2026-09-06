# Ollama Benchmark Results

## System Info

| Property | Value |
|----------|-------|
| CPU Model | CIX P1 CD8160 (Cortex-A720/A520) |
| CPU Count | 12 |
| RAM | 14.9 GB |
| Ollama Version | 0.31.2 |
| Date | 2026-08-18 |

---

## Model Comparison Results

| Model | Size | Prompt Eval (tokens/s) | Eval (tokens/s) | Total Time (s) | Response Length |
|-------|------|------------------------|-----------------|----------------|-----------------|
| driaforall/tiny-agent-a | 0.5b | 445.96 | 47.29 | 11.0 | 2061 |
| LiquidAI/lfm2.5-350m | 350m | 513.80 | 74.79 | 4.4 | 1094 |
| qwen3.5:0.8b | 0.8b | 210.96 | 30.33 | 71.9 | 0 (failed) |
| LiquidAI/lfm2.5-1.2b | 1.2b | 147.90 | 32.20 | 12.2 | 1430 |
| qwen2.5:1.5b | 1.5b | 108.70 | 25.07 | 21.7 | 2201 |
| phi4-mini | mini | 46.37 | 11.59 | 35.9 | 1714 |
| phi4-mini-reasoning | mini | - | - | - | Error |
| qwen3.5:4b | 4b | - | - | - | Error |
| gemma3:4b | 4b | 44.49 | 11.37 | 106.9 | 4907 |
| qwen2.5:7b | 7b | 24.21 | 7.26 | 96.4 | 3071 |
| qwen3-8b-unsloth (thinking) | 8b | 17.45 | 6.15 | 95.2 | 512 (capped) |
| qwen3-8b-unsloth (instruct) | 8b | 17.51 | 6.13 | 97.6 | 512 (capped) |

---

## Thread Scaling Test (qwen2.5:1.5b)

| Threads | Prompt Eval (tokens/s) | Eval (tokens/s) | Total Time (s) |
|---------|------------------------|-----------------|----------------|
| 1 | 29.59 | 10.30 | 36.09 |
| 2 | 55.77 | 16.73 | 31.06 |
| 4 | 107.15 | 24.44 | 31.62 |
| 6 | 147.88 | 28.07 | 20.91 |
| 8 | 182.08 | 29.00 | 20.18 |
| 12 | 93.11 | 12.50 | 39.42 |

---

## Key Findings

1. **Best Overall Speed**: LiquidAI/lfm2.5-350m (fastest at 4.4s total)
2. **Best Eval Rate**: LiquidAI/lfm2.5-350m at 74.79 tokens/s
3. **Thread Scaling**: Performance peaks at 8 threads, degrades at 12
4. **Failed Models**: phi4-mini-reasoning and qwen3.5:4b (JSON parse errors)