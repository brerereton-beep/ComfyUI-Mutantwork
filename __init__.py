# =============================================================================
# ComfyUI-Mutantwork — Mutant Power Pack
# Prompt Optimization + Forensic Analysis + Signature Injection
# mutantwork.com | @_Rickbot_
# =============================================================================

from .nodes.prompt_optimizer import MutantPromptOptimizer
from .nodes.forensic_lab import MutantForensicLab
from .nodes.mutant_signature import MutantSignature

# Maps class names to their Python class objects.
# ComfyUI uses this to register the nodes in the graph.
NODE_CLASS_MAPPINGS = {
    "MutantPromptOptimizer": MutantPromptOptimizer,
    "MutantForensicLab":     MutantForensicLab,
    "MutantSignature":       MutantSignature,
}

# Human-readable display names shown in the ComfyUI node menu.
NODE_DISPLAY_NAME_MAPPINGS = {
    "MutantPromptOptimizer": "🧬 Mutant Prompt Optimizer",
    "MutantForensicLab":     "🔬 Mutant Forensic Lab",
    "MutantSignature":       "⚗️  Mutant Signature",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
