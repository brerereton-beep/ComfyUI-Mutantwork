# =============================================================================
# MUTANT SIGNATURE NODE
# Injects an invisible metadata key into a PNG image before it is saved.
#
# PURPOSE:
#   Any image passed through this node gets a hidden PNG text chunk:
#       {"Mutantwork": "Optimized by Prompt Power"}
#
#   When that image is later uploaded to mutantwork.com/verify, the site
#   can instantly detect the chunk and confirm the image came from the suite.
#   This is a traceability and marketing tool — it does NOT alter pixels.
#
# USAGE:
#   Chain this node BEFORE any "Save Image" node in your workflow.
#   The image tensor passes through unchanged; metadata is baked into
#   a saved copy in your ComfyUI output folder.
#   Connect the output IMAGE to your Save Image node as normal.
#
# OPTIONAL FIELDS:
#   - custom_tag : override the default metadata value with your own string
#   - output_dir : folder to save the signed copy (defaults to ComfyUI output)
#   - filename_prefix : prefix for the saved filename
# =============================================================================

import os
import json
import datetime
import numpy as np
from PIL import Image, PngImagePlugin


# The key injected into the PNG tEXt chunk.
# Keep this consistent — mutantwork.com/verify reads this exact key.
MUTANT_METADATA_KEY = "Mutantwork"
MUTANT_METADATA_VAL = "Optimized by Prompt Power | mutantwork.com"


class MutantSignature:
    """
    ComfyUI node that bakes an invisible Mutantwork metadata signature
    into a PNG file. The image tensor is returned unchanged for further
    processing; a signed copy is written to the output directory.
    """

    CATEGORY = "Mutantwork"

    # ComfyUI requires OUTPUT_NODE = True for nodes that write files.
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                # Override the default metadata value
                "custom_tag": ("STRING", {
                    "default": MUTANT_METADATA_VAL,
                    "multiline": False,
                }),
                # Filename prefix for the saved file
                "filename_prefix": ("STRING", {
                    "default": "mutant_signed",
                    "multiline": False,
                }),
                # Absolute path to output folder.
                # If blank, uses ComfyUI's default output directory.
                "output_dir": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
            }
        }

    RETURN_TYPES  = ("IMAGE", "STRING")
    RETURN_NAMES  = ("image", "signature_log")
    FUNCTION      = "sign"

    def sign(self, image, custom_tag=MUTANT_METADATA_VAL,
             filename_prefix="mutant_signed", output_dir=""):

        log_lines = ["── MUTANT SIGNATURE ──"]

        # ── Resolve output directory ──────────────────────────────────────────
        if output_dir and output_dir.strip():
            save_dir = output_dir.strip()
        else:
            # Try to resolve ComfyUI's default output folder
            save_dir = self._resolve_output_dir()

        os.makedirs(save_dir, exist_ok=True)

        # ── Build PNG metadata payload ────────────────────────────────────────
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        tag_value = custom_tag if custom_tag.strip() else MUTANT_METADATA_VAL

        meta = PngImagePlugin.PngInfo()
        # Primary Mutantwork key (read by mutantwork.com/verify)
        meta.add_text(MUTANT_METADATA_KEY, tag_value)
        # Timestamp for traceability
        meta.add_text("Mutantwork-Timestamp", timestamp)
        # JSON manifest for richer parsing
        manifest = json.dumps({
            "signature": tag_value,
            "node":      "MutantSignature v1.0",
            "suite":     "ComfyUI-Mutantwork",
            "site":      "mutantwork.com",
            "signed_at": timestamp,
        })
        meta.add_text("Mutantwork-Manifest", manifest)

        # ── Convert tensor → PIL and save each image in batch ─────────────────
        pil_images = self._tensor_to_pil_list(image)
        saved_paths = []

        for i, pil_img in enumerate(pil_images):
            suffix   = f"_{i:04d}" if len(pil_images) > 1 else ""
            filename = f"{filename_prefix}{suffix}_{timestamp.replace(':', '-')}.png"
            save_path = os.path.join(save_dir, filename)

            pil_img.save(save_path, format="PNG", pnginfo=meta)
            saved_paths.append(save_path)
            log_lines.append(f"  Saved: {save_path}")

        log_lines.append(f"  Key   : {MUTANT_METADATA_KEY}")
        log_lines.append(f"  Value : {tag_value}")
        log_lines.append(f"  Time  : {timestamp}")
        log_lines.append("  ✅ Signature injected successfully")
        log_lines.append("")
        log_lines.append("  Upload to mutantwork.com/verify to confirm.")

        return (image, "\n".join(log_lines))

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _tensor_to_pil_list(image_tensor):
        """
        Convert a ComfyUI IMAGE tensor [B, H, W, C] into a list of PIL Images.
        Returns one PIL Image per item in the batch.
        """
        import torch

        if isinstance(image_tensor, torch.Tensor):
            tensor = image_tensor.cpu()
            if tensor.ndim == 3:
                tensor = tensor.unsqueeze(0)  # Add batch dimension
            arr = (tensor.numpy() * 255).clip(0, 255).astype(np.uint8)
        else:
            arr = (np.array(image_tensor) * 255).clip(0, 255).astype(np.uint8)
            if arr.ndim == 3:
                arr = arr[np.newaxis, ...]

        return [Image.fromarray(a, "RGB") for a in arr]

    @staticmethod
    def _resolve_output_dir():
        """
        Attempt to find ComfyUI's output directory by walking up from this
        file's location. Falls back to the current working directory.
        """
        here = os.path.dirname(os.path.abspath(__file__))
        # Walk up: nodes/ → ComfyUI-Mutantwork/ → custom_nodes/ → ComfyUI root
        for _ in range(4):
            candidate = os.path.join(here, "output")
            if os.path.isdir(candidate):
                return candidate
            here = os.path.dirname(here)

        # Last resort: cwd/output
        fallback = os.path.join(os.getcwd(), "output")
        os.makedirs(fallback, exist_ok=True)
        return fallback
