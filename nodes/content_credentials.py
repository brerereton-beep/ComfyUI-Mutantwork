# =============================================================================
# MutantContentCredentials — C2PA Content Credentials Node
# Embeds cryptographically signed provenance manifests into images.
# mutantwork.com | @_Rickbot_
# =============================================================================

import os
import io
import json
import torch
import numpy as np
from PIL import Image
import folder_paths
from datetime import datetime, timezone

# Try to import c2pa-python
try:
    import c2pa
    C2PA_AVAILABLE = True
except ImportError:
    C2PA_AVAILABLE = False

# Try to import cryptography for signing callback
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# Bundled test cert paths (shipped with this node)
_CERTS_DIR = os.path.join(os.path.dirname(__file__), "certs")
_BUNDLED_CERT = os.path.join(_CERTS_DIR, "es256_certs.pem")
_BUNDLED_KEY  = os.path.join(_CERTS_DIR, "es256_private.key")


class MutantContentCredentials:
    """
    Embeds a C2PA Content Credentials manifest into an image.
    Ships with bundled test certs — zero setup required.
    Optionally accepts custom PEM cert/key paths for real signing.
    """

    CATEGORY = "Mutantwork"
    FUNCTION = "sign_image"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "credentials_log")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "creator_name": ("STRING", {
                    "default": "Mutantwork",
                    "multiline": False
                }),
                "ai_model": ("STRING", {
                    "default": "ComfyUI",
                    "multiline": False
                }),
                "do_not_train": ("BOOLEAN", {"default": True}),
                "filename_prefix": ("STRING", {"default": "c2pa_signed"}),
            },
            "optional": {
                "custom_cert_pem": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Optional: path to your certificate .pem file. Leave blank to use bundled test cert."
                }),
                "custom_key_pem": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Optional: path to your private key .pem file."
                }),
            }
        }

    def sign_image(self, image, creator_name, ai_model, do_not_train,
                   filename_prefix, custom_cert_pem="", custom_key_pem=""):

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        output_dir = folder_paths.get_output_directory()
        output_filename = f"{filename_prefix}_{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.png"
        output_path = os.path.join(output_dir, output_filename)

        # Convert tensor to PIL image
        i = 255.0 * image[0].cpu().numpy()
        pil_image = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

        if not C2PA_AVAILABLE:
            pil_image.save(output_path)
            return (image, (
                "— CONTENT CREDENTIALS (FALLBACK) —\n"
                "⚠️  c2pa-python not installed.\n"
                "Run: pip install c2pa-python\n"
                f"Image saved without credentials: {output_path}"
            ))

        if not CRYPTO_AVAILABLE:
            pil_image.save(output_path)
            return (image, (
                "— CONTENT CREDENTIALS (FALLBACK) —\n"
                "⚠️  cryptography library not available.\n"
                "Run: pip install cryptography\n"
                f"Image saved without credentials: {output_path}"
            ))

        try:
            # Determine cert source
            using_custom = False
            if custom_cert_pem and custom_key_pem and \
               os.path.exists(custom_cert_pem) and os.path.exists(custom_key_pem):
                cert_path = custom_cert_pem
                key_path  = custom_key_pem
                using_custom = True
            elif os.path.exists(_BUNDLED_CERT) and os.path.exists(_BUNDLED_KEY):
                cert_path = _BUNDLED_CERT
                key_path  = _BUNDLED_KEY
            else:
                raise RuntimeError(
                    f"Bundled test certs not found at {_CERTS_DIR}. "
                    "Re-install the node from GitHub."
                )

            with open(cert_path, "rb") as f:
                cert_bytes = f.read()
            with open(key_path, "rb") as f:
                key_bytes = f.read()

            # Build signing callback
            def callback_signer(data: bytes) -> bytes:
                private_key = serialization.load_pem_private_key(
                    key_bytes,
                    password=None,
                    backend=default_backend()
                )
                return private_key.sign(data, ec.ECDSA(hashes.SHA256()))

            # Build C2PA manifest
            do_not_train_use = "notAllowed" if do_not_train else "allowed"
            manifest = {
                "title": f"Created by {creator_name}",
                "format": "image/png",
                "claim_generator": "Mutantwork Power Pack/1.0.0",
                "claim_generator_info": [
                    {"name": "Mutantwork Power Pack", "version": "1.0.0"}
                ],
                "assertions": [
                    {
                        "label": "c2pa.training-mining",
                        "data": {
                            "entries": {
                                "c2pa.ai_generative_training": {"use": do_not_train_use},
                                "c2pa.ai_inference": {"use": do_not_train_use}
                            }
                        }
                    },
                    {
                        "label": "stds.schema-org.CreativeWork",
                        "data": {
                            "@context": "https://schema.org/",
                            "@type": "CreativeWork",
                            "author": [{"@type": "Person", "name": creator_name}]
                        }
                    },
                    {
                        "label": "c2pa.actions",
                        "data": {
                            "actions": [
                                {
                                    "action": "c2pa.created",
                                    "softwareAgent": {
                                        "name": "Mutantwork Power Pack",
                                        "version": "1.0.0"
                                    },
                                    "parameters": {"aiModel": ai_model}
                                }
                            ]
                        }
                    }
                ]
            }

            # Save PIL to bytes stream
            input_stream = io.BytesIO()
            pil_image.save(input_stream, format="PNG")
            input_stream.seek(0)
            output_stream = io.BytesIO()

            with c2pa.Context() as context:
                with c2pa.Signer.from_callback(
                    callback_signer,
                    c2pa.C2paSigningAlg.ES256,
                    cert_bytes.decode("utf-8"),
                    "http://timestamp.digicert.com"
                ) as signer:
                    with c2pa.Builder(manifest, context) as builder:
                        builder.sign(signer, "image/png", input_stream, output_stream)

            with open(output_path, "wb") as f:
                f.write(output_stream.getvalue())

            cert_label = "Custom cert" if using_custom else "Bundled test cert"
            do_not_train_label = "notAllowed ✋" if do_not_train else "allowed"

            log = (
                f"— CONTENT CREDENTIALS —\n"
                f"Saved: {output_path}\n"
                f"Creator: {creator_name}\n"
                f"AI Model: {ai_model}\n"
                f"Time: {timestamp}\n"
                f"Do Not Train: {do_not_train_label}\n"
                f"Cert: {cert_label}\n"
                f"✅ C2PA manifest signed successfully\n\n"
                f"Upload to mutantwork.com/verify to confirm."
            )

            return (image, log)

        except Exception as e:
            pil_image.save(output_path)
            return (image, (
                f"— CONTENT CREDENTIALS (ERROR) —\n"
                f"⚠️  Signing failed: {str(e)}\n"
                f"Image saved unsigned: {output_path}"
            ))
