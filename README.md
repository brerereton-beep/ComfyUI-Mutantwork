# 🧬 ComfyUI-Mutantwork — The Mutant Power Pack

**A professional ComfyUI custom node suite for prompt optimization, local AI forensics, image provenance, and C2PA content credentials.**

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

---

### 🔬 Mutant Forensic Lab
**Local AI image detection. No API keys. No cloud. No cost.**

Runs three forensic pillars locally:

| Pillar | Method | What It Detects |
|--------|--------|-----------------|
| **A — Metadata** | PNG/EXIF text chunk extraction | ComfyUI workflow JSON, A1111 parameters, Midjourney tags, camera EXIF |
| **B — FFT Analysis** | 2D Fast Fourier Transform | Latent grid artifacts at 8/16/32px intervals from VAE decoder upsampling |
| **C — ELA** | Error Level Analysis | Inconsistent compression cycles indicating composited or edited images |

**Outputs:** `image` (pass-through) + `forensic_report` (scored text report with verdict)

---

### ⚗️ Mutant Signature
**Injects an invisible provenance key into your PNG before saving.**

Bakes a PNG `tEXt` chunk into every output:
```
Key:   Mutantwork
Value: Optimized by Prompt Power | mutantwork.com
```

Images signed by this node can be instantly verified at **[mutantwork.com/verify](https://mutantwork.com/verify)**.

---

### 🔏 Mutant Content Credentials
**Embeds a cryptographically signed C2PA manifest into your image.**

C2PA (Coalition for Content Provenance and Authenticity) is the open standard backed by Adobe, Microsoft, Google, the BBC, and major media organisations for verifiable media provenance.

**What it does:**
- Signs your image with a cryptographic manifest — tamper-evident and verifiable
- Embeds a **"Do Not Train"** assertion (AI training mining: notAllowed)
- Records creator name, AI model, and timestamp
- Signed images are verified at **[mutantwork.com/verify](https://mutantwork.com/verify)** — drop in your image and the C2PA badge appears instantly

**Ships with bundled test certs — zero setup required.** Optionally accepts your own PEM certificate for production signing.

**Controls:**
| Input | Description |
|-------|-------------|
| `creator_name` | Your name or brand (default: Mutantwork) |
| `ai_model` | The model used to generate the image |
| `do_not_train` | Embeds C2PA "notAllowed" training assertion when enabled |
| `filename_prefix` | Output filename prefix |
| `custom_cert_pem` | Optional: path to your own PEM certificate |
| `custom_key_pem` | Optional: path to your own PEM private key |

**Requires:** `pip install c2pa-python cryptography`

---

## Installation

### Option 1 — Manual
1. Clone into your `ComfyUI/custom_nodes/` folder:
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/brerereton-beep/ComfyUI-Mutantwork.git
```

2. Install dependencies:
```bash
pip install -r ComfyUI-Mutantwork/requirements.txt
```

3. Restart ComfyUI. Nodes appear under the **"Mutantwork"** category.

### Option 2 — ComfyUI Manager
Search for `ComfyUI-Mutantwork` in ComfyUI Manager → Install.

---

## Example Workflow

```
[Load Image] ──→ [Mutant Forensic Lab] ──→ [Mutant Signature] ──→ [Mutant Content Credentials] ──→ [Save Image]
                         ↓                          ↓                           ↓
                  [Display Any]              [Display Any]              [Display Any]
               (forensic_report)           (signature_log)           (credentials_log)

[Mutant Prompt Optimizer] ──→ [CLIP Text Encode] ──→ [KSampler...]
```

---

## Requirements

```
numpy>=1.24.0
Pillow>=10.0.0
scipy>=1.11.0
opencv-python>=4.8.0
c2pa-python>=0.32.0
```

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
