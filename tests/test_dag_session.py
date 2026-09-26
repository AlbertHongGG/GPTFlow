from gpt_flow.domain.entities import ConversationTree
from gpt_flow.domain.enums import AuthorRole


class TestConversationTree:
    """Test conversation DAG structure and lineage navigation."""

    def test_empty_tree(self) -> None:
        tree = ConversationTree()
        assert tree.conversation_id is None
        assert tree.current_node_id is None
        assert tree.get_parent_id() == "client-created-root"
        assert len(tree.messages) == 0

    def test_multi_turn_lineage(self) -> None:
        tree = ConversationTree(conversation_id="conv-test-1", title="Test Tree")

        # 1. First user message
        m1 = tree.add_message(
            role=AuthorRole.USER,
            content="Hello",
        )
        assert tree.current_node_id == m1.id
        assert m1.parent_id is None
        assert tree.get_parent_id() == m1.id

        # 2. Assistant response
        m2 = tree.add_message(
            role=AuthorRole.ASSISTANT,
            content="Hello! How can I help you?",
            thinking_content="User greeted kindly.",
            system_hints=["reason"],
        )
        assert tree.current_node_id == m2.id
        assert m2.parent_id == m1.id
        assert m2.thinking_content == "User greeted kindly."
        assert tree.get_parent_id() == m2.id

        # 3. Second user message
        m3 = tree.add_message(
            role=AuthorRole.USER,
            content="What is 1 + 1?",
        )
        assert m3.parent_id == m2.id
        assert tree.current_node_id == m3.id
        assert len(tree.messages) == 3

    def test_tree_serialization(self) -> None:
        tree = ConversationTree(conversation_id="conv-serialize-1")
        tree.add_message(role=AuthorRole.USER, content="Ping")
        tree.add_message(role=AuthorRole.ASSISTANT, content="Pong")

        json_str = tree.model_dump_json()
        restored = ConversationTree.model_validate_json(json_str)

        assert restored.conversation_id == "conv-serialize-1"
        assert len(restored.messages) == 2
        assert restored.current_node_id == tree.current_node_id
