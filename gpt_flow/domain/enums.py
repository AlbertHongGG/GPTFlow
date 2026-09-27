from enum import Enum


class ModelKind(str, Enum):
    """Supported model identifiers."""

    AUTO = "auto"
    GPT_6_LUNA = "gpt-6-luna"
    GPT_6_SOL = "gpt-6-sol"
    GPT_6_ASTRA = "gpt-6-astra"


class AuthorRole(str, Enum):
    """Message author roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class StreamEventType(str, Enum):
    """Server-Sent Event categories."""

    THINKING = "thinking"
    CONTENT = "content"
    STATUS = "status"
    ERROR = "error"
    DONE = "done"


class PrepareSource(str, Enum):
    """Origin of speculative prepare calls."""

    COMPOSER_EDITOR_STATE = "composer_editor_state"
    CONTEXT_CHANGE = "context_change"


class PrepareState(str, Enum):
    """Client prepare dispatch states."""

    NONE = "none"
    SUCCESS = "success"
    SENT = "sent"
