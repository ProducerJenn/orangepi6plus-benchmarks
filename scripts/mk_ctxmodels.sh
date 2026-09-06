#!/bin/bash
set -e
mk() {
  local SRC="$1" NAME="$2" CTX="$3" TEMP="${4:-0.7}" TOPP="${5:-0.8}"
  cat > /tmp/opencode/Modelfile-cctx <<MOD
FROM $SRC
PARAMETER num_ctx $CTX
PARAMETER temperature $TEMP
PARAMETER top_p $TOPP
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
MOD
  ollama rm "$NAME" >/dev/null 2>&1 || true
  ollama create "$NAME" -f /tmp/opencode/Modelfile-cctx | tail -1
  echo "created $NAME (ctx=$CTX)"
}

mk "hf.co/LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M" "lfm2.5-8b-16k" 16384
mk "LiquidAI/lfm2.5-1.2b-instruct:latest" "lfm2.5-1.2b-16k" 16384
mk "gemma3:4b" "gemma3-4b-16k" 16384
mk "qwen3.5:4b" "qwen3.5-4b-16k" 16384
mk "qwen2.5:7b" "qwen2.5-7b-16k" 16384
mk "phi4-mini:latest" "phi4-mini-8k" 8192
mk "qwen3:latest" "qwen3-8b-16k" 16384
mk "hf.co/unsloth/Qwen3-8B-GGUF:UD-Q4_K_XL" "qwen3-8b-unsloth-16k" 16384
