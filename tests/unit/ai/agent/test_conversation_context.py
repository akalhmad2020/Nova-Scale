from app.ai.application.agent.conversation_context import (
    ConversationContext,
    ConversationMessage,
)


def test_conversation_context_is_empty_without_messages() -> None:
    context = ConversationContext()

    assert context.messages == ()
    assert context.is_empty is True


def test_conversation_context_contains_previous_messages() -> None:
    context = ConversationContext(
        messages=(
            ConversationMessage(
                role="user",
                content="Compare SHIP-001 and SHIP-002.",
            ),
            ConversationMessage(
                role="assistant",
                content="SHIP-001 is currently more delayed.",
            ),
        )
    )

    assert context.is_empty is False
    assert len(context.messages) == 2

    assert context.messages[0].role == "user"
    assert context.messages[0].content == ("Compare SHIP-001 and SHIP-002.")

    assert context.messages[1].role == "assistant"
    assert context.messages[1].content == ("SHIP-001 is currently more delayed.")
