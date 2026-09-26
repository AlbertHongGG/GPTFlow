from enum import Enum


class ModelKind(str, Enum):
    """Supported model identifiers."""

    AUTO = "auto"
    O1 = "o1"
    O1_MINI = "o1-mini"
    O3_MINI = "o3-mini"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"


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
