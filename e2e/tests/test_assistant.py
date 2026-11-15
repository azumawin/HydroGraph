"""The health assistant's chat: the one control that writes to the backend.

Whether a model is configured decides what comes back -- a reply, or the 503
reason the chat shows verbatim -- so these pin the plumbing either way: the
suggested question is sent, the pending line appears, and an answer replaces it.
The reply's content is the backend's business (`api/test_assistant.py`).
"""

import dashboard as ui
from playwright.sync_api import Page, expect

STARTER = "Summarize the current findings and tell me what to do."


def test_the_suggested_question_is_sent_and_answered(dashboard: Page) -> None:
    expect(ui.chat_starter(dashboard)).to_be_visible()
    expect(ui.chat_messages(dashboard)).to_have_count(0)

    ui.chat_starter(dashboard).click()

    expect(ui.chat_messages(dashboard, "user")).to_have_text(STARTER)
    # The suggestion gives way to the conversation it started.
    expect(ui.chat_starter(dashboard)).to_have_count(0)
    # Either the model's reply or the backend's reason for being unavailable,
    # and the "Thinking…" line gone once it arrives.
    expect(
        dashboard.locator(
            ".vitals-dashboard-chat-message.is-assistant:not(.is-pending),"
            " .vitals-dashboard-chat-message.is-error"
        )
    ).to_have_count(1, timeout=30000)
    expect(ui.chat_messages(dashboard, "pending")).to_have_count(0)


def test_the_composer_only_sends_a_question_that_has_text(dashboard: Page) -> None:
    expect(ui.chat_send(dashboard)).to_be_disabled()

    # Whitespace is not a question.
    ui.chat_input(dashboard).fill("   ")
    expect(ui.chat_send(dashboard)).to_be_disabled()

    ui.chat_input(dashboard).fill("Is the crew member stable?")
    expect(ui.chat_send(dashboard)).to_be_enabled()

    ui.chat_send(dashboard).click()
    expect(ui.chat_messages(dashboard, "user")).to_have_text("Is the crew member stable?")
    # Sending clears the box, so the next question starts empty.
    expect(ui.chat_input(dashboard)).to_have_value("")
