# 🧬 ComfyUI-Mutantwork — The Mutant Power Pack

**A professional ComfyUI custom node suite for prompt optimization, local AI forensics, and image provenance.**

Built by [Mutantwork](https://mutantwork.com) — AI tools built different.

---

## Nodes

### 🧬 Mutant Prompt Optimizer
Implements the **Word Weight methodology** to combat Semantic Saturation.

Most "quality" tokens (`masterpiece`, `4k`, `highly detailed`) have been seen so often in training data that the model partially ignores them. They consume token budget without activating specific latent directions.

**What it does:**
- **De-noises** your prompt by stripping saturated tokens that dilute latent space
- **Injects weighted replacements** — maps weak generic phrases to high-density, precisely targeted equivalents
- Example: `good lighting` → `(cinematic rim lighting:1.3)`

**Controls:**
| Input | Description |
|-------|-------------|
| `prompt` | Your raw prompt |
| `enable_denoise` | Toggle stripping of inflated tokens |
| `enable_weighting` | Toggle word weight injection |
| `weight_scale` | Global multiplier on all injected weights (0.5–1.5) |

**Outputs:** `optimized_prompt` (ready for CLIP Text Encode) + `optimization_report`

The Word Weight Dictionary is an editable Python dict at the top of `nodes/prompt_optimizer.py` — add your own mappings in the same format.

---

### 🔬 Mutant Forensic Lab
**Local AI image detection. No API keys. No cloud. No cost.**

Runs three forensic pillars locally:

| Pillar | Method | What It Detects |
|--------|--------|-----------------|
| **A — Metadata** | PNG/EXIF text chunk extraction | ComfyUI workflow JSON, A1111 parameters, Midjourney tags, camera EXIF |
| **B — FFT Analysis** | 2D Fast Fourier Transform | Latent grid artifacts at 8/16/32px intervals from VAE decoder upsampling |
| **C — ELA** | Error Level Analysis | Inconsistent compression cycles indicating composited or edited images |

**Why FFT detects AI images:**
Diffusion models operate in latent space where 1 latent pixel = 8 spatial pixels. The VAE decoder's upsampling introduces periodic energy at those intervals. In the Fourier domain, this appears as a cross-axis spike pattern — the "Digital Grid". Natural photographs don't show this.

**Outputs:** `image` (pass-through) + `forensic_report` (scored text report with verdict)

---

### ⚗️ Mutant Signature
**Injects an invisible provenance key into your PNG before saving.**

Bakes a PNG `tEXt` chunk into every output:
```
Key:   Mutantwork
Value: Optimized by Prompt Power | mutantwork.com
```

Images signed by this node can be instantly verified at **[mutantwork.com/verify](https://mutantwork.com/verify)** — the site reads the metadata and confirms the Mutant Signature on upload.

Chain this node before your Save Image node. The image tensor passes through unchanged; a signed copy is written to your output directory.

---

## Installation

### Option 1 — Manual
1. Clone or download this repo into your `ComfyUI/custom_nodes/` folder:
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/brerereton/ComfyUI-Mutantwork.git
```

2. Install dependencies (numpy and Pillow are usually already present):
```bash
pip install -r ComfyUI-Mutantwork/requirements.txt
```

3. Restart ComfyUI. The nodes appear under the **"Mutantwork"** category.

### Option 2 — ComfyUI Manager
Search for `ComfyUI-Mutantwork` in ComfyUI Manager → Install.

---

## Example Workflow

```
[Load Image] ──→ [Mutant Forensic Lab] ──→ [Mutant Signature] ──→ [Save Image]
                         ↓                          ↓
                  [Display Any]              [Display Any]
               (forensic_report)           (signature_log)

[Mutant Prompt Optimizer] ──→ [CLIP Text Encode] ──→ [KSampler...]
         ↓
  [Display Any]
(optimized_prompt)
```

---

## Requirements

```
numpy>=1.24.0
Pillow>=10.0.0
scipy>=1.11.0
opencv-python>=4.8.0
```

NumPy and Pillow are bundled with most ComfyUI installations.

---

## Verify Signatures

Images processed through the **Mutant Signature** node carry a hidden PNG metadata key.
Upload them to **[mutantwork.com/verify](https://mutantwork.com/verify)** — the site confirms the signature and runs full AI forensic analysis.

---

## Expanding the Word Weight Dictionary

Open `nodes/prompt_optimizer.py`. The `WORD_WEIGHT_DICT` is at the top of the file.

Add entries in this format:
```python
"your weak phrase": "(your strong weighted phrase:1.3)",
```

Weight scale: `1.0` = neutral, `1.1–1.3` = moderate boost, `1.4–1.5` = strong.

---

## Part of the Mutantwork Suite

| Tool | Platform | Link |
|------|----------|------|
| **Prompt Power Pro** | Chrome Extension | [Gumroad](https://breretonian.gumroad.com/l/btfbkg) |
| **Mutant Verify** | Web | [mutantwork.com/verify](https://mutantwork.com/verify) |
| **NI Trade Guard Pro** | Web | [ni-trade-guard.streamlit.app](https://ni-trade-guard.streamlit.app) |
| **ComfyUI-Mutantwork** | ComfyUI | This repo |

---

## License

MIT — free to use, modify, and distribute.

---

*Built by [@_Rickbot_](https://x.com/_Rickbot_) — mutantwork.com*
