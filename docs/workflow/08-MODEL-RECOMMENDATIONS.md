# 08 — Model Recommendations

> Recommended models for RTX 4060 (8 GB VRAM) / 16 GB RAM.
> Dedicated model per input type. All verified to fit within budget.

---

## Hardware Constraint

```
┌──────────────────────────────────────────────────────┐
│  GPU: RTX 4060 — 8 GB VRAM (CUDA 3072 cores)       │
│  RAM: 16 GB system memory                           │
│                                                      │
│  Rule: ONE major model loaded at a time              │
│  Strategy: Load → Infer → Unload → Next              │
│  Quantization: AWQ/GPTQ 4-bit on all LLMs/VLMs      │
│  Headroom: Keep ~1 GB free for CUDA overhead         │
└──────────────────────────────────────────────────────┘
```

---

## Recommended Model Matrix

| # | Task | Recommended Model | VRAM (4-bit) | HuggingFace ID | Why This Model |
|---|------|-------------------|-------------|----------------|----------------|
| 1 | **VQA + Caption** | Qwen2.5-VL-7B-Instruct AWQ | ~5.5 GB | `Qwen/Qwen2.5-VL-7B-Instruct-AWQ` | Best VLM under 8GB, native multi-image, excellent structured output |
| 2 | **Grounding (Detection)** | Grounding DINO Tiny | ~0.7 GB | `IDEA-Research/grounding-dino-tiny` | Open-vocab detection, text→bbox, lightweight |
| 3 | **Grounding (Segmentation)** | SAM 2.1 Hiera Tiny | ~0.35 GB | `facebook/sam2.1-hiera-tiny` | Meta's latest, near-ViT-H quality at 1/16th size |
| 4 | **Change Detection** | TinyCD | ~0.15 GB | `github: AndreaCodeworksField/TinyCD` | 5M params, SOTA on LEVIR-CD, trains easily on 8GB |
| 5 | **Change VQA** | Qwen2.5-VL-7B (shared) | ~5.5 GB | Same as #1 | Native multi-image = trivial bi-temporal input |
| 6 | **Optical-SAR Fusion** | Custom EfficientNet-B0 fusion | ~0.5 GB | Train on BigEarthNet-MM | Lightweight dual-encoder + cross-attention |
| 7 | **Agent Router** | Rule-based (primary) | 0 GB | N/A | Deterministic, no VRAM needed |

> [!TIP]
> Models #1 and #5 share the same backbone — VQA and Change VQA use the same Qwen2.5-VL-7B. This means you only download/fine-tune ONE VLM.

---

## Detailed Recommendations

### 1. VQA + Captioning — Qwen2.5-VL-7B-Instruct AWQ

**Why Qwen2.5-VL-7B over alternatives:**

| Criteria | Qwen2.5-VL-7B | InternVL2-8B | GeoChat-7B |
|----------|---------------|--------------|------------|
| VRAM (4-bit) | 5.5 GB ✅ | 6.5 GB ⚠️ | 5 GB ✅ |
| Multi-image | ✅ Native | ❌ Hacks needed | ❌ Single only |
| Dynamic resolution | ✅ | ❌ Fixed 448px | ❌ Fixed |
| JSON output | Excellent | Good | Poor |
| RS pre-training | ❌ (needs LoRA) | ❌ | ✅ Built-in |
| Overall quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

**Key advantage:** Native multi-image support means bi-temporal and optical-SAR pairs can be fed directly — no concatenation hacks.

**Captioning** is done by prompting the same model differently. Zero extra VRAM.

**Download:**
```bash
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-AWQ --local-dir models/vqa/qwen25vl
```

**Backup:** InternVL2-4B (`OpenGVLab/InternVL2-4B`) — only 3.5 GB, use if Qwen is too tight.

---

### 2 & 3. Grounding — Grounding DINO + SAM 2.1

```
User query: "Highlight the water body"
          ↓
Grounding DINO (0.7 GB) → bounding boxes
          ↓
SAM 2.1 Hiera-Tiny (0.35 GB) → pixel-precise masks
          ↓
Overlay on image → visual evidence
──────────────────────────────────
Total: ~1.1 GB (both loaded simultaneously ✅)
```

**Why this combo:**
- GDINO: Text→bbox, no class training needed
- SAM 2.1 Tiny: 38.9M params but near-ViT-H quality (78.5 vs 79.1 mIoU)
- Combined < 1.1 GB — leaves room for agent LLM if needed

**Download:**
```bash
huggingface-cli download IDEA-Research/grounding-dino-tiny --local-dir models/grounding/gdino
# SAM 2.1 via pip install sam2, then download checkpoint
```

**Backup:** Florence-2-large (`microsoft/Florence-2-large`) — single model for detection + grounding (~1.5 GB)

---

### 4. Change Detection — TinyCD

**Why TinyCD:**
- 5M params, ~150 MB VRAM — absurdly lightweight
- F1 89.6 on LEVIR-CD (near SOTA)
- Full training fits on 8 GB with room to spare
- Designed specifically for efficient change detection

| CD Model | Params | F1 (LEVIR) | VRAM |
|----------|--------|-----------|------|
| **TinyCD** | 5M | 89.6 | 150 MB ✅ |
| BIT | 3.5M | 89.3 | 200 MB ✅ |
| ChangeFormer-b0 | 11M | 90.4 | 400 MB ✅ |
| SNUNet-c32 | 12M | 88.2 | 300 MB ✅ |

All of these fit. TinyCD is recommended for smallest footprint.

**GitHub:** `https://github.com/AndreaCodeworksField/TinyCD`
**Framework:** Use Open-CD (`https://github.com/open-cd/open-cd`) for standardized training.

**Backup:** BIT — slightly larger, comparable quality.

---

### 5. Change VQA — Qwen2.5-VL (Shared Backbone)

**Strategy:** Same model as VQA (#1), with 2 images in the prompt.

```
Image T1 + Image T2 + Question
         ↓
  Qwen2.5-VL (native multi-image)
         ↓
  "The built-up area has increased..."
```

**Enhanced approach:** Feed the TinyCD change map as a 3rd image:
```
Image T1 + Image T2 + Change Map + Question
         ↓
  Qwen2.5-VL (3 images in prompt)
         ↓
  Better-grounded answer
```

**No extra download needed** — same model as VQA.

---

### 6. Optical-SAR Fusion — Custom EfficientNet-B0 Dual Encoder

```
Optical → EfficientNet-B0 → features (320-dim)
                                    ↓
                             Cross-attention
                             fusion module
                                    ↓
SAR ──→ EfficientNet-B0 → features (320-dim)
                                    ↓
                          Classification head
                                    ↓
                          Land cover map
                          (built-up, water, vegetation, etc.)
```

**VRAM:** ~500 MB total
**Training data:** BigEarthNet-MM (Sentinel-2 + Sentinel-1 pairs, 19 classes)
**Training time:** 4-8 hours on RTX 4060

**Alternative for POC:** Skip the custom network, feed both images to Qwen2.5-VL with a system prompt explaining optical vs SAR. This is weaker but ships faster.

---

### 7. Agent Router — Rule-Based (No Model Needed)

For the POC, the rule-based router uses **zero GPU**. It's keyword matching + input analysis.

**Future upgrade:** Add Qwen2.5-3B-Instruct AWQ (~2 GB) as LLM fallback for ambiguous queries.

---

## VRAM Budget Per Scenario

| Demo Scenario | Models Loaded | Peak VRAM | Fits? |
|--------------|---------------|-----------|-------|
| VQA | Qwen2.5-VL-7B AWQ | 5.5 GB | ✅ |
| Captioning | Qwen2.5-VL-7B AWQ (reuse) | 5.5 GB | ✅ |
| Grounding | GDINO + SAM 2.1 Tiny | 1.1 GB | ✅ |
| Change Detection | TinyCD → Qwen2.5-VL | 5.5 GB peak | ✅ |
| Change VQA | TinyCD → Qwen2.5-VL | 5.5 GB peak | ✅ |
| Optical-SAR | Fusion net → Qwen2.5-VL | 6.0 GB peak | ✅ |
| ❌ All at once | Everything | ~17 GB | ❌ |

---

## "Zero-Swap" Alternative (Lower Quality, Instant Response)

If demo speed matters more than quality, load ALL models simultaneously:

```
┌────────────────────────────────────────────────────────┐
│  Florence-2-large (VQA/Caption/Grounding)  ~1.5 GB   │
│  SAM 2.1 Hiera-Tiny (Segmentation)         ~0.35 GB  │
│  TinyCD (Change Detection)                 ~0.15 GB  │
│  ─────────────────────────────────────────────────    │
│  Total:                                    ~2.0 GB   │
│  Free headroom:                            ~6.0 GB   │
│  Model swapping needed:                    NONE ✅    │
└────────────────────────────────────────────────────────┘
```

Trade-off: Florence-2 is weaker than Qwen2.5-VL-7B but eliminates all loading delays.

---

## Fine-Tuning Recommendations

| What to Fine-Tune | Dataset | Method | VRAM | Time |
|-------------------|---------|--------|------|------|
| Qwen2.5-VL-7B LoRA | VRSBench VQA + BigEarthNet | QLoRA (4-bit base + LoRA adapters) | ~8 GB | 4-8 hours |
| TinyCD | LEVIR-CD | Full fine-tuning | ~1 GB | 2-4 hours |
| Fusion network | BigEarthNet-MM | Full training from scratch | ~2 GB | 4-8 hours |

> [!IMPORTANT]
> Fine-tuning Qwen2.5-VL-7B with QLoRA will use ~8 GB — your entire VRAM budget. Close all other GPU processes during training. Alternatively, use Google Colab Pro / RunPod for training (~$1-2/hour).

---

## Download Script

```bash
#!/bin/bash
# download_models.sh — Run ONCE before development starts

pip install huggingface_hub

echo "=== Qwen2.5-VL-7B AWQ (VQA + Caption + Change VQA) ==="
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-AWQ --local-dir models/vqa/qwen25vl

echo "=== Grounding DINO Tiny ==="
huggingface-cli download IDEA-Research/grounding-dino-tiny --local-dir models/grounding/gdino

echo "=== SAM 2.1 Hiera Tiny ==="
# Install sam2 package and download checkpoint
pip install sam2
python -c "from sam2.build_sam import build_sam2; print('SAM2 ready')"

echo "=== TinyCD ==="
git clone https://github.com/AndreaCodeworksField/TinyCD.git models/change/tinycd

echo "=== Backup: Florence-2-large ==="
# huggingface-cli download microsoft/Florence-2-large --local-dir models/backup/florence2

echo "All models downloaded!"
```

---

## Decision Matrix: When to Use What

| If you need... | Use | Load alongside |
|---------------|-----|----------------|
| Best VQA quality | Qwen2.5-VL-7B AWQ | Nothing else (5.5 GB) |
| Fastest grounding | GDINO + SAM 2.1 Tiny | Can coexist (1.1 GB) |
| Change detection map | TinyCD | Can load with anything (0.15 GB) |
| Fastest everything | Florence-2 + SAM + TinyCD | All fit (~2 GB) |
| No GPU at all | Rule-based router + no output responses | CPU only |
