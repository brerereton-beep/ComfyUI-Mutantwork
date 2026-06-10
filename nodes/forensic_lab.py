# =============================================================================
# MUTANT FORENSIC LAB — Local Forensic Engine
# Provides "Evidence" rather than "Opinions". Runs 100% locally. No API calls.
#
# THREE EVIDENCE PILLARS:
#
# PILLAR A — METADATA EXTRACTION
#   Reads hidden PNG/WEBP text chunks and EXIF data. Identifies origin:
#   ComfyUI (workflow JSON), Automatic1111 (parameters block), Midjourney
#   (Description tag), or genuine camera (EXIF Make/Model present).
#
# PILLAR B — FFT FREQUENCY ANALYSIS
#   AI diffusion models process images in a latent space where 1 latent pixel
#   = 8 spatial pixels (standard VAE). The decoder upsamples back to full res,
#   introducing periodic energy at intervals of 8, 16, 32 pixels. In the
#   Fourier domain this appears as cross-axis spectral peaks — the "Digital
#   Grid". Natural photographs do NOT show this pattern.
#   Detection method: 2D FFT → magnitude spectrum → count cross-axis peaks
#   at expected AI grid frequencies.
#
# PILLAR C — ERROR LEVEL ANALYSIS (ELA)
#   Every JPEG re-save degrades quality uniformly. If an image has been
#   composited or edited, different regions will show different ELA "heat"
#   because they've been through different numbers of compression cycles.
#   High ELA std deviation + localized hot spots = composite/manipulated.
#   Method: re-compress to known JPEG quality → subtract → measure variance.
# =============================================================================

import io
import json
import re

import numpy as np
from PIL import Image


# ── SCORING THRESHOLDS ────────────────────────────────────────────────────────
# Adjust these if you want to tune sensitivity.
FFT_GRID_THRESHOLD   = 0.60   # Magnitude fraction above which a peak is "significant"
FFT_PEAK_WEIGHT      = 0.40   # Contribution of FFT pillar to total score (0–1)
ELA_WEIGHT           = 0.30   # Contribution of ELA pillar
META_WEIGHT          = 0.30   # Contribution of metadata pillar
ELA_RESAVE_QUALITY   = 90     # JPEG quality for ELA re-compression step


class MutantForensicLab:
    """
    ComfyUI node that performs local forensic analysis on an image tensor.
    Outputs the original image (pass-through) and a detailed forensic report.
    """

    CATEGORY = "Mutantwork"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # ComfyUI IMAGE tensor: [B, H, W, C] float32 in [0, 1]
                "image": ("IMAGE",),
            },
            "optional": {
                # Absolute path to the original file on disk.
                # Needed for metadata extraction (PNG text chunks, EXIF).
                # Leave blank if you only want FFT + ELA analysis.
                "image_path": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES  = ("IMAGE", "STRING")
    RETURN_NAMES  = ("image", "forensic_report")
    FUNCTION      = "analyze"

    # ── MAIN ENTRY POINT ──────────────────────────────────────────────────────
    def analyze(self, image, image_path=""):
        # Convert ComfyUI tensor → PIL Image for analysis
        pil_img = self._tensor_to_pil(image)
        img_np  = np.array(pil_img)  # uint8 [H, W, 3]

        report_sections = []
        report_sections.append("╔══════════════════════════════════════╗")
        report_sections.append("║    MUTANT FORENSIC LAB — REPORT      ║")
        report_sections.append("╚══════════════════════════════════════╝\n")

        # ── PILLAR A: METADATA ────────────────────────────────────────────────
        meta_score, meta_section = self._pillar_metadata(pil_img, image_path)
        report_sections.append(meta_section)

        # ── PILLAR B: FFT FREQUENCY ANALYSIS ─────────────────────────────────
        fft_score, fft_section = self._pillar_fft(img_np)
        report_sections.append(fft_section)

        # ── PILLAR C: ELA ─────────────────────────────────────────────────────
        ela_score, ela_section = self._pillar_ela(pil_img)
        report_sections.append(ela_section)

        # ── COMPOSITE SCORE ───────────────────────────────────────────────────
        composite = (
            meta_score * META_WEIGHT +
            fft_score  * FFT_PEAK_WEIGHT +
            ela_score  * ELA_WEIGHT
        )
        composite = round(min(100.0, max(0.0, composite)), 1)

        verdict = self._verdict(composite)
        integrity = self._integrity(meta_score, ela_score)

        report_sections.append("─" * 40)
        report_sections.append(f"MUTANT PROBABILITY SCORE : {composite}%")
        report_sections.append(f"VERDICT                  : {verdict}")
        report_sections.append(f"INTEGRITY LEVEL          : {integrity}")
        report_sections.append("─" * 40)

        full_report = "\n".join(report_sections)
        return (image, full_report)

    # ──────────────────────────────────────────────────────────────────────────
    # PILLAR A — METADATA EXTRACTION
    # ──────────────────────────────────────────────────────────────────────────
    def _pillar_metadata(self, pil_img, image_path):
        lines = ["[PILLAR A] METADATA ANALYSIS"]
        score = 0.0

        # Gather all info from PIL (works even without a file path)
        info = pil_img.info or {}

        # Load from file for richer EXIF if path provided
        if image_path and image_path.strip():
            try:
                with Image.open(image_path.strip()) as src:
                    info = {**src.info, **info}
            except Exception as e:
                lines.append(f"  [!] Could not open file path: {e}")

        origin = "Unknown / No Origin Metadata"
        workflow_json = None
        extra_keys = []

        # ── Detect ComfyUI ────────────────────────────────────────────────────
        if "workflow" in info:
            origin = "ComfyUI (workflow JSON detected)"
            score += 85.0
            try:
                workflow_json = json.loads(info["workflow"])
                node_count = len(workflow_json.get("nodes", []))
                lines.append(f"  ComfyUI workflow: {node_count} nodes found")
            except Exception:
                lines.append("  ComfyUI workflow: present but not parseable JSON")

        elif "prompt" in info:
            origin = "ComfyUI (prompt metadata present)"
            score += 75.0

        # ── Detect Automatic1111 ───────────────────────���──────────────────────
        elif "parameters" in info:
            origin = "Automatic1111 / WEBUI"
            score += 85.0
            params = info["parameters"][:200]
            lines.append(f"  A1111 parameters (first 200 chars): {params}")

        # ── Detect Midjourney ─────────────────────────────────────────────────
        elif any(
            "midjourney" in str(info.get(k, "")).lower()
            for k in ("Description", "Software", "Comment")
        ):
            origin = "Midjourney"
            score += 90.0

        # ── Real camera (EXIF present) ────────────────────────────────────────
        else:
            try:
                exif_data = pil_img.getexif()
                make  = exif_data.get(271, "")   # Make tag
                model = exif_data.get(272, "")   # Model tag
                if make or model:
                    origin = f"Camera: {make} {model}".strip()
                    score += 5.0  # Real camera EXIF = likely organic
                    lines.append(f"  Camera Make: {make}")
                    lines.append(f"  Camera Model: {model}")
                else:
                    # No EXIF, no AI metadata — stripped or ambiguous
                    score += 30.0
                    lines.append("  No EXIF Make/Model found (possibly stripped)")
            except Exception:
                score += 20.0
                lines.append("  EXIF unreadable")

        # ── Mutantwork Signature ──────────────────────────────────────────────
        if "Mutantwork" in info:
            lines.append(f"  ✅ Mutant Signature: {info['Mutantwork']}")

        # ── List all raw PNG text keys ────────────────────────────────────────
        for k, v in info.items():
            if isinstance(v, str) and k not in ("workflow", "parameters", "prompt"):
                preview = v[:80].replace("\n", " ")
                extra_keys.append(f"  [{k}]: {preview}")

        lines.append(f"  ORIGIN DETECTED: {origin}")
        if extra_keys:
            lines.append("  RAW METADATA KEYS:")
            lines.extend(extra_keys[:10])  # cap at 10 keys

        return (round(min(100.0, score), 1), "\n".join(lines))

    # ─────────────────���────────────────────────────────────────────────────────
    # PILLAR B — FFT FREQUENCY ANALYSIS ("Digital Grid Detection")
    # ──────────────────────────────────────────────────────────────────────────
    def _pillar_fft(self, img_np):
        """
        Detect the periodic latent-grid artifact using the 2D Fourier Transform.

        WHY THIS WORKS:
        Diffusion models work in a compressed latent space (typically 8x downscale).
        The VAE decoder reconstructs the image by upsampling, which introduces
        periodic energy at multiples of the latent grid frequency (8px, 16px, 32px).
        In the FFT magnitude spectrum, this energy appears as bright peaks along
        the horizontal and vertical axes — the "cross" or "Digital Grid" pattern.
        Real photographs exhibit a smooth 1/f² spectral falloff with no such peaks.

        SCORING:
        We count significant cross-axis peaks at AI-expected frequencies.
        0–3 peaks   → low AI probability
        4–8 peaks   → moderate
        9+ peaks    → high AI probability
        """
        lines = ["\n[PILLAR B] FFT FREQUENCY ANALYSIS"]

        try:
            # Convert to float64 grayscale [H, W]
            gray = np.mean(img_np.astype(np.float64), axis=2)
            h, w = gray.shape

            # 2D Fast Fourier Transform
            fft2  = np.fft.fft2(gray)
            fshift = np.fft.fftshift(fft2)

            # Log magnitude spectrum — log1p prevents log(0) issues
            magnitude  = np.log1p(np.abs(fshift))
            mag_max    = magnitude.max()
            if mag_max < 1e-8:
                lines.append("  FFT magnitude too low — image may be uniform colour")
                return (0.0, "\n".join(lines))

            # Normalise to [0, 1]
            mag_norm = magnitude / mag_max

            center_h, center_w = h // 2, w // 2

            # ── Build a mask to exclude the DC component (centre blob) ────────
            # DC is always the brightest point — it's the mean of the image,
            # not a forensic signal.
            Y, X    = np.ogrid[:h, :w]
            dc_r    = max(4, min(h, w) // 25)
            dc_mask = ((Y - center_h)**2 + (X - center_w)**2) > dc_r**2
            mag_masked = mag_norm * dc_mask

            # ── Scan horizontal and vertical axes through centre ───────────────
            # A 6-pixel-wide strip around each axis captures cross-axis energy.
            h_strip = mag_masked[
                max(0, center_h - 3) : min(h, center_h + 4), :
            ]
            v_strip = mag_masked[
                :, max(0, center_w - 3) : min(w, center_w + 4)
            ]

            horiz_profile = h_strip.max(axis=0)  # shape: [w]
            vert_profile  = v_strip.max(axis=1)   # shape: [h]

            # ── Count significant spectral peaks ──────────────────────────────
            # A peak is "significant" if it exceeds FFT_GRID_THRESHOLD of the
            # maximum value in its axis profile.
            h_max   = horiz_profile.max()
            v_max   = vert_profile.max()
            h_thresh = h_max * FFT_GRID_THRESHOLD if h_max > 0.3 else 1.0
            v_thresh = v_max * FFT_GRID_THRESHOLD if v_max > 0.3 else 1.0

            h_peaks = int(np.sum(horiz_profile > h_thresh))
            v_peaks = int(np.sum(vert_profile  > v_thresh))

            # ── Check for peaks specifically at AI latent grid frequencies ────
            # Expected intervals: every h/8, h/16, h/32 pixels from centre
            grid_hits = 0
            grid_hit_desc = []
            for period in [8, 16, 32, 64]:
                freq_h = max(1, h // period)
                freq_w = max(1, w // period)
                for mult in range(1, 5):
                    for sign in [1, -1]:
                        ph = center_h + sign * freq_h * mult
                        pw = center_w + sign * freq_w * mult
                        if 0 <= ph < h and 0 <= pw < w:
                            roi = mag_masked[
                                max(0, ph-2) : min(h, ph+3),
                                max(0, pw-2) : min(w, pw+3)
                            ]
                            if roi.size and roi.max() > FFT_GRID_THRESHOLD:
                                grid_hits += 1
                                grid_hit_desc.append(
                                    f"{period}px grid @ ({'±'}{freq_h * mult},{freq_w * mult})"
                                )

            # ── Convert to 0–100 score ────────────────────────────────────────
            # Natural images: typically 0–4 grid hits, 0–10 axis peaks
            # AI images: typically 6–20+ grid hits, 20–100+ axis peaks
            peak_score = min(100.0, (h_peaks + v_peaks) / max(1, (h + w) / 10) * 100)
            grid_score = min(100.0, grid_hits / 12.0 * 100)
            fft_score  = peak_score * 0.45 + grid_score * 0.55

            grid_detected = grid_hits >= 3

            lines.append(f"  Cross-axis spectral peaks : H={h_peaks}, V={v_peaks}")
            lines.append(f"  Latent grid hits (8/16/32/64px) : {grid_hits}")
            if grid_hit_desc:
                for d in grid_hit_desc[:5]:
                    lines.append(f"    → {d}")
            lines.append(f"  Digital Grid Detected     : {'YES ⚠' if grid_detected else 'No'}")
            lines.append(f"  FFT Pillar Score          : {round(fft_score, 1)}/100")

            return (round(fft_score, 1), "\n".join(lines))

        except Exception as e:
            lines.append(f"  [ERROR] FFT analysis failed: {e}")
            return (0.0, "\n".join(lines))

    # ──────────────────────────────────────────────────────────────────────────
    # PILLAR C — ERROR LEVEL ANALYSIS (ELA)
    # ──────────────────────────────────────────────────────────────────────────
    def _pillar_ela(self, pil_img):
        """
        Detect composite/edited regions by analysing re-compression differences.

        HOW ELA WORKS:
        When a JPEG is saved at a known quality level, every pixel is compressed
        uniformly. If you subtract the re-compressed version from the original,
        a truly original image shows a very uniform, low-level "heat map".
        A composite or edited image shows HOT SPOTS where different regions have
        been through different numbers of compression cycles — they degrade at
        different rates, leaving visible discrepancies in the difference image.

        HIGH ELA std dev + localized hot spots = composite/manipulated image.
        VERY UNIFORM ELA = single-origin image (either truly original or AI-gen
        at first save — so low ELA alone does NOT rule out AI generation).

        SCORING:
        ELA contributes to the Mutant Probability only when it shows COMPOSITE
        evidence. A clean ELA does NOT add to the AI score.
        """
        lines = ["\n[PILLAR C] ERROR LEVEL ANALYSIS (ELA)"]

        try:
            # ── Re-compress to known JPEG quality ─────────────────────────────
            rgb_img = pil_img.convert("RGB")
            buffer  = io.BytesIO()
            rgb_img.save(buffer, format="JPEG", quality=ELA_RESAVE_QUALITY)
            buffer.seek(0)
            recompressed = Image.open(buffer).convert("RGB")

            # ── Calculate pixel-level difference ──────────────────────────────
            orig_np   = np.array(rgb_img,      dtype=np.float32)
            recomp_np = np.array(recompressed, dtype=np.float32)
            ela_np    = np.abs(orig_np - recomp_np)

            # ── Statistical analysis ───────────────────────────────────────────
            ela_mean  = float(np.mean(ela_np))
            ela_std   = float(np.std(ela_np))
            ela_max   = float(np.max(ela_np))
            ela_p95   = float(np.percentile(ela_np, 95))

            # ── Detect localised hot spots (composite evidence) ───────────────
            # Divide image into 8x8 blocks and compare block means.
            # High variance across blocks = inconsistent compression history.
            h, w, _ = ela_np.shape
            block_sz = max(8, min(h, w) // 16)
            block_means = []
            for y in range(0, h - block_sz, block_sz):
                for x in range(0, w - block_sz, block_sz):
                    block = ela_np[y:y+block_sz, x:x+block_sz]
                    block_means.append(np.mean(block))

            block_variance = float(np.std(block_means)) if block_means else 0.0
            hotspot_ratio  = float(np.mean(ela_np > ela_p95))

            # ── ELA score ─────────────────────────────────────────────────────
            # Only penalise for COMPOSITE signals (high std + hot spots).
            # We deliberately DON'T reward low ELA as AI evidence here
            # (that's handled by FFT + metadata pillars).
            std_score      = min(100.0, ela_std       * 4.0)
            variance_score = min(100.0, block_variance * 5.0)
            ela_score      = std_score * 0.5 + variance_score * 0.5

            integrity = "ORIGINAL / SINGLE COMPRESSION CYCLE"
            if ela_score > 60:
                integrity = "COMPOSITE / MULTI-CYCLE COMPRESSION DETECTED"
            elif ela_score > 35:
                integrity = "POSSIBLY RESAVED OR EDITED"

            lines.append(f"  ELA Mean          : {ela_mean:.2f}")
            lines.append(f"  ELA Std Dev       : {ela_std:.2f}")
            lines.append(f"  ELA Max           : {ela_max:.2f}")
            lines.append(f"  Block Variance    : {block_variance:.3f}")
            lines.append(f"  Hot-spot Ratio    : {hotspot_ratio:.3f}")
            lines.append(f"  Integrity         : {integrity}")
            lines.append(f"  ELA Pillar Score  : {round(ela_score, 1)}/100")

            return (round(ela_score, 1), "\n".join(lines))

        except Exception as e:
            lines.append(f"  [ERROR] ELA analysis failed: {e}")
            return (0.0, "\n".join(lines))

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _tensor_to_pil(image_tensor):
        """Convert ComfyUI IMAGE tensor [B, H, W, C] → PIL Image (RGB)."""
        import torch
        if isinstance(image_tensor, torch.Tensor):
            img = image_tensor[0] if image_tensor.ndim == 4 else image_tensor
            arr = (img.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        else:
            arr = (np.array(image_tensor) * 255).clip(0, 255).astype(np.uint8)
            if arr.ndim == 4:
                arr = arr[0]
        return Image.fromarray(arr, "RGB")

    @staticmethod
    def _verdict(score):
        if score >= 80:
            return "CRITICAL MUTATION FOUND — High confidence AI-generated"
        elif score >= 60:
            return "PROBABLE MUTATION — Likely AI-generated"
        elif score >= 40:
            return "INCONCLUSIVE — Mixed or ambiguous signals"
        elif score >= 20:
            return "LOW SIGNAL — Possibly organic or first-save AI"
        else:
            return "BIOLOGICAL SIGNATURE — Likely organic / camera source"

    @staticmethod
    def _integrity(meta_score, ela_score):
        if ela_score > 60:
            return "COMPROMISED — composite or multi-edit evidence"
        elif meta_score > 70:
            return "AI-NATIVE — single generation, no resave evidence"
        else:
            return "INTACT — appears to be original single-save file"
