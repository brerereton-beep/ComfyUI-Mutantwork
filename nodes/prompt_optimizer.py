# =============================================================================
# MUTANT PROMPT OPTIMIZER
# Implements the "Word Weight" methodology to combat Semantic Saturation.
#
# Theory: Common "quality" tokens (masterpiece, 4k, highly detailed) have been
# seen so often in training data that the model has learned to partially ignore
# them. They occupy token budget without activating specific latent directions.
#
# Solution:
#   1. DE-NOISE: Strip saturated tokens that dilute latent space.
#   2. WEIGHT INJECT: Replace weak generic phrases with high-density, weighted
#      equivalents that target specific latent directions with precision.
#
# HOW TO EXPAND:
#   - Add words to INFLATED_WORDS to strip them automatically.
#   - Add entries to WORD_WEIGHT_DICT to map weak phrases to heavy ones.
#   - Weight format: (phrase:strength) — 1.0 neutral, 1.1–1.5 stronger.
# =============================================================================

import re

# =============================================================================
# STEP 1: INFLATED WORDS — Tokens to strip (Semantic Saturation)
# These tokens appear so frequently in training data that they've lost
# specificity. They consume token budget without adding directional signal.
# The list is checked as whole words/phrases (case-insensitive).
# =============================================================================
INFLATED_WORDS = [
    # Overused quality tokens
    "masterpiece", "best quality", "high quality", "highest quality",
    "good quality", "excellent quality", "superior quality", "ultra quality",
    "8k", "4k", "2k", "8k resolution", "4k resolution", "2k resolution",
    "hd", "full hd", "ultra hd", "uhd", "fhd", "1080p", "4k uhd",
    "highly detailed", "ultra detailed", "extremely detailed", "very detailed",
    "super detailed", "hyper detailed", "insanely detailed", "incredibly detailed",
    "intricate details", "intricate detail", "intricate",

    # Vague superlatives — too broad to activate anything specific
    "stunning", "breathtaking", "mesmerizing", "awe-inspiring",
    "amazing", "incredible", "fantastic", "magnificent",
    "spectacular", "extraordinary", "exceptional",
    "perfect", "flawless", "impeccable",

    # Platform/render tokens — largely decorative in modern models
    "trending on artstation", "artstation", "deviantart",
    "award winning", "award-winning", "award-winning photography",
    "professional", "professional photography", "professional quality",
    "unreal engine", "unreal engine 5", "octane render", "blender render",
    "vray", "cycles render",

    # Catch-all detail tokens that get replaced by weighted versions below
    "sharp focus", "crisp", "crisp details", "pristine",
]

# =============================================================================
# STEP 2: WORD WEIGHT DICTIONARY — "Weak-to-Heavy" Phrase Mappings
#
# Format: "input phrase" : "(ComfyUI weighted output:strength)"
#
# These transform generic descriptors into latent-space-specific activations.
# The weighted syntax (phrase:weight) tells CLIP to attend MORE to that token.
# Weight 1.0 = neutral. 1.1 = slight boost. 1.3 = strong. 1.5 = very strong.
#
# HOW TO EXPAND: Just add a new line below in the same format.
# =============================================================================
WORD_WEIGHT_DICT = {

    # ── LIGHTING ──────────────────────────────────────────────────────���──────
    "good lighting":     "(cinematic rim lighting:1.3)",
    "nice lighting":     "(three-point studio lighting:1.3)",
    "soft light":        "(diffused softbox lighting:1.2)",
    "soft lighting":     "(diffused softbox lighting:1.2)",
    "dramatic lighting": "(chiaroscuro high-contrast lighting:1.4)",
    "dark lighting":     "(low-key film noir lighting:1.3)",
    "bright lighting":   "(high-key studio lighting:1.2)",
    "natural lighting":  "(golden hour natural diffused light:1.3)",
    "sunlight":          "(warm golden hour sunlight rays:1.2)",
    "moonlight":         "(cool diffused silver moonlight:1.2)",
    "neon lights":       "(neon glow volumetric light bleed:1.3)",
    "neon":              "(neon glow volumetric emission:1.3)",
    "glowing":           "(bioluminescent emission glow:1.3)",
    "backlit":           "(backlit rim light silhouette halo:1.3)",
    "candlelight":       "(warm flickering candlelight:1.3)",
    "studio lighting":   "(professional three-point studio lighting:1.2)",
    "harsh light":       "(hard directional harsh light:1.3)",
    "volumetric":        "(volumetric god rays light shafts:1.3)",

    # ── FOCUS & DEPTH ─────────────────────────────────────────────────────────
    "sharp":             "(tack sharp macro precision focus:1.2)",
    "in focus":          "(precise razor-sharp depth of field:1.2)",
    "blurry background": "(shallow depth bokeh background blur:1.3)",
    "bokeh":             "(creamy f1.4 lens bokeh:1.3)",
    "depth of field":    "(cinematic shallow depth of field:1.2)",

    # ── REALISM ───────────────────────────────────────────────────────────────
    "realistic":         "(hyperrealistic photographic rendering:1.3)",
    "photorealistic":    "(photorealistic 35mm photography:1.3)",
    "lifelike":          "(hyperrealistic lifelike rendering:1.3)",
    "real":              "(photographic realism:1.2)",
    "cinematic":         "(anamorphic cinematic widescreen:1.2)",
    "film look":         "(analog 35mm film grain:1.2)",
    "vintage photo":     "(faded vintage color process:1.2)",

    # ── FACES & ANATOMY ───────────────────────────────────────────────────────
    "detailed face":     "(hyperrealistic facial anatomy:1.3)",
    "pretty face":       "(symmetrical facial structure:1.2)",
    "beautiful face":    "(symmetrical high-cheekbone model face:1.3)",
    "expressive eyes":   "(detailed iris pupil limbal ring:1.3)",
    "eyes":              "(photorealistic iris and pupil:1.2)",
    "detailed eyes":     "(photorealistic iris limbal ring cornea:1.3)",
    "hair":              "(fine strand-by-strand hair simulation:1.2)",
    "flowing hair":      "(dynamic wind-swept hair simulation:1.3)",
    "skin":              "(subsurface scattering pore texture skin:1.3)",
    "skin texture":      "(subsurface scattering micropore detail:1.3)",
    "hands":             "(anatomically correct hand and finger detail:1.2)",

    # ── ATMOSPHERE ────────────────────────────────────────────────────────────
    "dark":              "(deep shadow tonal range:1.2)",
    "dark atmosphere":   "(oppressive moody atmospheric depth:1.3)",
    "moody":             "(cinematic moody desaturated atmosphere:1.3)",
    "fog":               "(atmospheric volumetric fog rays:1.3)",
    "smoke":             "(volumetric smoke particle simulation:1.3)",
    "mist":              "(low ground ethereal mist:1.2)",
    "rain":              "(dynamic rainfall wet surface reflections:1.3)",
    "storm":             "(dramatic storm clouds lightning:1.3)",
    "dust":              "(golden dust particle suspension:1.2)",

    # ── COLOUR & PALETTE ──────────────────────────────────────────────────────
    "colorful":          "(vibrant chromatic saturation:1.3)",
    "colourful":         "(vibrant chromatic saturation:1.3)",
    "vibrant":           "(vivid chromatic intensity punch:1.3)",
    "dark colors":       "(desaturated noir color palette:1.2)",
    "dark colours":      "(desaturated noir color palette:1.2)",
    "warm colors":       "(warm amber orange color grade:1.2)",
    "warm colours":      "(warm amber orange color grade:1.2)",
    "cool colors":       "(cool teal blue color grade:1.2)",
    "cool colours":      "(cool teal blue color grade:1.2)",
    "black and white":   "(high contrast silver gelatin monochrome:1.3)",
    "monochrome":        "(high contrast monochrome tonal range:1.2)",
    "sepia":             "(warm sepia-toned aged photograph:1.2)",
    "pastel":            "(soft pastel desaturated palette:1.2)",

    # ── COMPOSITION ───────────────────────────────────────────────────────────
    "portrait":          "(tight crop portrait framing:1.1)",
    "landscape":         "(wide cinematic landscape composition:1.1)",
    "close up":          "(extreme close-up macro lens:1.2)",
    "close-up":          "(extreme close-up macro lens:1.2)",
    "wide shot":         "(ultra wide anamorphic lens shot:1.2)",
    "overhead":          "(top-down aerial bird-eye perspective:1.2)",
    "bird eye":          "(aerial bird-eye orthographic view:1.2)",
    "bird's eye":        "(aerial bird-eye orthographic view:1.2)",
    "symmetrical":       "(bilateral symmetry geometric composition:1.2)",
    "low angle":         "(extreme low angle worm's eye view:1.2)",

    # ── MATERIALS & SURFACES ──────────────────────────────────────────────────
    "metal":             "(metallic PBR specular surface:1.2)",
    "shiny":             "(specular highlight reflection:1.2)",
    "glossy":            "(glossy lacquer surface sheen:1.2)",
    "rough":             "(rough tactile surface displacement:1.2)",
    "texture":           "(fine micro surface normal detail:1.2)",
    "fabric":            "(woven fabric thread weave detail:1.2)",
    "silk":              "(shimmering silk drape:1.3)",
    "leather":           "(aged cracked leather grain:1.2)",
    "glass":             "(refractive glass caustic:1.3)",
    "crystal":           "(refractive crystal prism formation:1.3)",
    "gold":              "(polished gold metallic reflection:1.3)",
    "chrome":            "(mirror chrome metallic surface:1.3)",
    "rust":              "(oxidized rust patina:1.2)",
    "concrete":          "(brutalist rough concrete surface:1.2)",

    # ── NATURAL ELEMENTS ──────────────────────────────────────────────────────
    "water":             "(fluid caustic water surface:1.3)",
    "ocean":             "(vast ocean wave caustics:1.2)",
    "fire":              "(dynamic flame particle system:1.3)",
    "lightning":         "(electric arc lightning bolt:1.3)",
    "ice":               "(translucent fractured ice crystal:1.3)",
    "rock":              "(detailed geological rock formation:1.2)",
    "wood":              "(fine grain wood texture:1.2)",
    "leaves":            "(detailed leaf vein macro:1.2)",

    # ── ENVIRONMENTS ──────────────────────────────────────────────────────────
    "forest":            "(ancient dense primeval forest canopy:1.2)",
    "city":              "(dense urban megacity skyline:1.2)",
    "night":             "(moonlit nocturnal scene:1.2)",
    "sunset":            "(magic hour golden sunset:1.3)",
    "sunrise":           "(dawn golden hour sunrise:1.3)",
    "space":             "(cosmic nebula deep space stars:1.3)",
    "underwater":        "(deep underwater caustic scene:1.2)",
    "desert":            "(vast arid sand dune formation:1.2)",
    "mountains":         "(dramatic alpine mountain range:1.2)",
    "snow":              "(pristine snow surface micro-texture:1.2)",
    "cave":              "(subterranean cave stalactite:1.2)",

    # ── ARTISTIC STYLES ───────────────────────────────────────────────────────
    "oil painting":      "(impasto oil painting technique:1.2)",
    "watercolor":        "(loose wet-on-wet watercolor wash:1.2)",
    "watercolour":       "(loose wet-on-wet watercolor wash:1.2)",
    "sketch":            "(detailed graphite pencil rendering:1.1)",
    "anime style":       "(high-quality anime key visual:1.2)",
    "comic":             "(bold comic book line art:1.2)",
    "retro":             "(retro analog halftone print:1.2)",
    "futuristic":        "(sleek cyberpunk neo-future aesthetic:1.2)",
    "dark fantasy":      "(gothic dark fantasy grimoire aesthetic:1.3)",
    "sci-fi":            "(hard science fiction technical aesthetic:1.2)",
    "minimalist":        "(clean minimalist negative space:1.1)",
    "surreal":           "(surrealist dream logic composition:1.2)",
    "impressionist":     "(impressionist loose brushwork:1.2)",
}


class MutantPromptOptimizer:
    """
    ComfyUI node that applies the Word Weight methodology to a raw prompt.
    Strips semantic saturation tokens and injects weighted phrase replacements.
    """

    CATEGORY = "Mutantwork"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "a beautiful woman with stunning eyes, 8k, masterpiece, highly detailed"
                }),
            },
            "optional": {
                # Toggle de-noising pass independently
                "enable_denoise": ("BOOLEAN", {"default": True}),
                # Toggle word weight injection independently
                "enable_weighting": ("BOOLEAN", {"default": True}),
                # Global scale multiplier applied to all injected weights.
                # 1.0 = use dictionary values as-is. 0.8 = soften. 1.2 = push harder.
                "weight_scale": ("FLOAT", {
                    "default": 1.0, "min": 0.5, "max": 1.5, "step": 0.05
                }),
            }
        }

    RETURN_TYPES  = ("STRING", "STRING")
    RETURN_NAMES  = ("optimized_prompt", "optimization_report")
    FUNCTION      = "optimize"

    def optimize(self, prompt, enable_denoise=True, enable_weighting=True, weight_scale=1.0):
        report_lines = ["── MUTANT PROMPT OPTIMIZER REPORT ──\n"]
        stripped     = []
        injected     = []
        working      = prompt.strip()

        # ── PASS 1: WORD WEIGHT INJECTION ─────────────────────────────────────
        # Run before de-noising so we catch phrases before their component
        # words might be partially stripped.
        if enable_weighting:
            # Sort by length descending so longer phrases are matched first,
            # preventing partial matches (e.g. "soft lighting" before "soft").
            for weak, heavy in sorted(WORD_WEIGHT_DICT.items(), key=lambda x: -len(x[0])):
                pattern = re.compile(re.escape(weak), re.IGNORECASE)
                if pattern.search(working):
                    # Apply weight_scale by parsing and rescaling the weight value.
                    scaled_heavy = self._scale_weight(heavy, weight_scale)
                    working = pattern.sub(scaled_heavy, working)
                    injected.append(f"  '{weak}' → {scaled_heavy}")

        # ── PASS 2: DE-NOISING ────────────────────────────────────────────────
        # Strip saturated tokens. Sort by length descending (same reason).
        if enable_denoise:
            for token in sorted(INFLATED_WORDS, key=lambda x: -len(x)):
                pattern = re.compile(
                    r'(?<![(\w])' + re.escape(token) + r'(?![\w)])',
                    re.IGNORECASE
                )
                if pattern.search(working):
                    working = pattern.sub("", working)
                    stripped.append(f"  '{token}'")

        # ── CLEANUP ───────────���───────────────────────────────────────────────
        # Collapse multiple commas, spaces; trim leading/trailing comma.
        working = re.sub(r',\s*,+', ',', working)
        working = re.sub(r'\s{2,}', ' ', working)
        working = working.strip(" ,")

        # ── BUILD REPORT ──────────────────────────────────────────────────────
        if injected:
            report_lines.append(f"[WEIGHT INJECTIONS: {len(injected)}]")
            report_lines.extend(injected)
        else:
            report_lines.append("[WEIGHT INJECTIONS: 0 — no matches in dictionary]")

        if stripped:
            report_lines.append(f"\n[STRIPPED TOKENS: {len(stripped)}]")
            report_lines.extend(stripped)
        else:
            report_lines.append("\n[STRIPPED TOKENS: 0 — prompt already clean]")

        report_lines.append(f"\n[ORIGINAL]\n  {prompt.strip()}")
        report_lines.append(f"\n[OPTIMIZED]\n  {working}")

        return (working, "\n".join(report_lines))

    @staticmethod
    def _scale_weight(weighted_phrase: str, scale: float) -> str:
        """
        Parse a (phrase:weight) token and apply the global weight_scale multiplier.
        Example: "(cinematic rim lighting:1.3)" with scale 1.2 → "(cinematic rim lighting:1.56)"
        Clamps result to range [0.5, 2.0].
        """
        if scale == 1.0:
            return weighted_phrase

        def _rescale(match):
            phrase  = match.group(1)
            weight  = float(match.group(2))
            scaled  = round(min(2.0, max(0.5, weight * scale)), 2)
            return f"({phrase}:{scaled})"

        return re.sub(r'\((.+?):(\d+\.?\d*)\)', _rescale, weighted_phrase)
