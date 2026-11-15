"""Source parsers. Each returns a :class:`~agentic_inference_refunds.records.SourceResult`."""

from . import claude_code, codex, copilot, generic

LOADERS = {
    "claude-code": claude_code.load,
    "codex": codex.load,
    "copilot": copilot.load,
    "usage": generic.load,
}

__all__ = ["LOADERS", "claude_code", "codex", "copilot", "generic"]
