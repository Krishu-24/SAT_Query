# 08 — Model Recommendations

> Recommended model stack for an RTX 4060 with 8 GB VRAM and 16 GB system memory.

## Hardware Constraints

```text
GPU: RTX 4060 — 8 GB VRAM
RAM: 16 GB system memory
Strategy: load one major model at a time, run inference, then unload
Quantization: AWQ/GPTQ 4-bit for VLMs and LLMs when possible
Headroom: maintain roughly 1 GB for CUDA overhead
```

## Recommended Model Matrix

| # | Task | Recommended model | VRAM (4-bit) | Hugging Face ID | Why it fits |
|---|---|---|---:|---|---|
| 1 | VQA + captioning | Qwen2.5-VL-7B-Instruct AWQ | ~5.5 GB | `Qwen/Qwen2.5-VL-7B-Instruct-AWQ` | best VLM under 8 GB with native multi-image support |
| 2 | Grounding detection | Grounding DINO Tiny | ~0.7 GB | `IDEA-Research/grounding-dino-tiny` | lightweight open-vocabulary object detection |
| 3 | Grounding segmentation | SAM 2.1 Hiera Tiny | ~0.35 GB | `facebook/sam2.1-hiera-tiny` | precise masks without excess memory use |
| 4 | Change detection | TinyCD | ~0.15 GB | `github: AndreaCodeworksField/TinyCD` | compact model with strong LEVIR-CD performance |
| 5 | Change VQA | Qwen2.5-VL-7B (shared backbone) | ~5.5 GB | same as #1 | native support for paired-image reasoning |
| 6 | Optical-SAR fusion | EfficientNet-B0 dual encoder | ~0.5 GB | train on BigEarthNet-MM | compact cross-modal feature fusion |
| 7 | Agent router | rule-based router | 0 GB | N/A | deterministic and zero-VRAM |

The VQA and change-VQA paths can share the same VLM backbone, which keeps the architecture simpler and reduces download burden.

## Detailed Recommendations

### 1. VQA and Captioning

Qwen2.5-VL-7B-Instruct AWQ is the strongest default choice under the VRAM constraint.

| Criteria | Qwen2.5-VL-7B | InternVL2-8B | GeoChat-7B |
|---|---|---|---|
| VRAM (4-bit) | 5.5 GB | 6.5 GB | 5 GB |
| Multi-image support | native | requires workarounds | limited |
| Dynamic resolution | supported | fixed 448px | fixed |
| Structured output | strong | good | weak |
| Remote-sensing adaptation | requires LoRA | requires adaptation | built-in |

Key advantage: native multi-image support makes bi-temporal and optical-SAR workflows straightforward.

Download:

```bash
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-AWQ --local-dir models/vqa/qwen25vl
```

Backup option: `OpenGVLab/InternVL2-4B` with ~3.5 GB footprint if the Qwen path is too constrained.

### 2. Grounding Detection and Segmentation

```text
User query: "Highlight the water body"
            ↓
Grounding DINO (0.7 GB) → bounding boxes
            ↓
SAM 2.1 Hiera Tiny (0.35 GB) → masks
            ↓
Overlay on image → evidence output
Total: ~1.1 GB
```

Why this combination works:

- Grounding DINO: text-to-box localization without a rigid class vocabulary
- SAM 2.1 Tiny: mask generation tuned for precise region extraction
- combined memory footprint remains manageable for the project budget

Download:

```bash
huggingface-cli download IDEA-Research/grounding-dino-tiny --local-dir models/grounding/gdino
```

SAM 2.1 is typically installed via the `sam2` package and the respective checkpoint.

### 3. Change Detection

TinyCD is the preferred default because it is compact, fast, and still competitive on LEVIR-CD.

| Model | Params | F1 (LEVIR) | VRAM |
|---|---:|---:|---:|
| TinyCD | 5M | 89.6 | 150 MB |
| BIT | 3.5M | 89.3 | 200 MB |
| ChangeFormer-b0 | 11M | 90.4 | 400 MB |
| SNUNet-c32 | 12M | 88.2 | 300 MB |

TinyCD is the best fit when memory and speed matter most.

### 4. Change VQA

Use the same VLM as the general VQA workflow, but feed it two images and the question together. For better grounding, add the change map as a third input image.

```text
Image T1 + Image T2 + Question
          ↓
Qwen2.5-VL multi-image inference
          ↓
Answer describing change direction or magnitude
```

This keeps model count low and avoids introducing a second large multimodal backbone.

### 5. Optical-SAR Fusion

```text
Optical → EfficientNet-B0 → feature extraction
             ↓
             cross-attention fusion
             ↓
SAR → EfficientNet-B0 → feature extraction
             ↓
         classification head
             ↓
        land-cover output
```

Training data: BigEarthNet-MM (Sentinel-2 + Sentinel-1 pairs)

Memory footprint: approximately 500 MB for the network itself.

This is a practical POC option, even if the final system may later prefer a more specialized remote-sensing fusion stack.

### 6. Agent Router

The rule-based router is the preferred solution for the demo because it uses zero GPU memory and provides deterministic routing behavior.

It is a strong production-quality POC choice and should remain the default path unless ambiguity or high variability in the query set becomes a dominant issue.

## VRAM Budget by Scenario

| Scenario | Models loaded | Peak VRAM | Fits budget |
|---|---|---:|---|
| VQA | Qwen2.5-VL-7B AWQ | 5.5 GB | Yes |
| Captioning | Qwen2.5-VL-7B AWQ | 5.5 GB | Yes |
| Grounding | GDINO + SAM 2.1 Tiny | 1.1 GB | Yes |
| Change detection | TinyCD → Qwen2.5-VL | 5.5 GB peak | Yes |
| Change VQA | TinyCD → Qwen2.5-VL | 5.5 GB peak | Yes |
| Optical-SAR | fusion net → Qwen2.5-VL | 6.0 GB peak | Yes |
| All models at once | full stack | ~17 GB | No |

## Fine-Tuning Recommendations

| Target | Dataset | Method | VRAM | Time |
|---|---|---|---:|---:|
| Qwen2.5-VL-7B LoRA | VRSBench + BigEarthNet | QLoRA | ~8 GB | 4–8 hours |
| TinyCD | LEVIR-CD | full fine-tuning | ~1 GB | 2–4 hours |
| fusion network | BigEarthNet-MM | full training | ~2 GB | 4–8 hours |

For Qwen training, plan for a near-full VRAM budget. A cloud GPU or a workstation with little competing workload is strongly preferred.

## Download Script

```bash
#!/bin/bash
pip install huggingface_hub

echo "Downloading Qwen2.5-VL-7B AWQ"
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct-AWQ --local-dir models/vqa/qwen25vl

echo "Downloading Grounding DINO"
huggingface-cli download IDEA-Research/grounding-dino-tiny --local-dir models/grounding/gdino

echo "Installing SAM 2.1 dependency"
pip install sam2

echo "Cloning TinyCD"
git clone https://github.com/AndreaCodeworksField/TinyCD.git models/change/tinycd

echo "Model download complete"
```

## Decision Matrix

| Need | Best option | Notes |
|---|---|---|
| strongest general VQA | Qwen2.5-VL-7B AWQ | default recommendation |
| lowest memory cost | TinyCD + rule router | best for constrained runtime |
| best region grounding | GDINO + SAM 2.1 Tiny | precise mask generation |
| best bi-temporal reasoning | Qwen2.5-VL with paired inputs | strong multi-image support |
| best optical-SAR analysis | fusion network + VLM | appropriate for demo and downstream work |
| Fastest grounding | GDINO + SAM 2.1 Tiny | Can coexist (1.1 GB) |
| Change detection map | TinyCD | Can load with anything (0.15 GB) |
| Fastest everything | Florence-2 + SAM + TinyCD | All fit (~2 GB) |
| No GPU at all | Rule-based router + no output responses | CPU only |
