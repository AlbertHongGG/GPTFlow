import json
import logging
from pathlib import Path

from gpt_flow.domain.entities import ConversationTree
from gpt_flow.domain.interfaces import ISessionRepository

logger = logging.getLogger("gpt_flow.session_store")


class FileSessionRepository(ISessionRepository):
    """File-based repository storing conversation trees as JSON files."""

    def __init__(self, sessions_dir: Path) -> None:
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, session_id: str) -> Path:
        # Sanitize session_id to avoid path traversal
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        return self.sessions_dir / f"{safe_id}.json"

    def load(self, session_id: str) -> ConversationTree | None:
        """Load conversation tree from disk."""
        path = self._get_path(session_id)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ConversationTree.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to load session from {path}: {e}")
            return None

    def save(self, conversation: ConversationTree) -> None:
        """Persist conversation tree to disk."""
        if not conversation.conversation_id:
            logger.warning(
                "Attempted to save conversation tree without conversation_id."
            )
            return

        path = self._get_path(conversation.conversation_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    conversation.model_dump(mode="json"),
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.debug(f"Saved conversation {conversation.conversation_id} to {path}")
        except Exception as e:
            logger.error(f"Failed to save session to {path}: {e}")

    def list_sessions(self) -> list[str]:
        """List all saved session IDs."""
        return [p.stem for p in self.sessions_dir.glob("*.json")]

    def delete(self, session_id: str) -> bool:
        """Delete a saved session."""
        path = self._get_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False
