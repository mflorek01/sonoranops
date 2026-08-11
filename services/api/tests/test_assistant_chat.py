from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.assistant_chat import _final, governed_chat


class FakeResponses:
    def __init__(self, terminal_status: str | None = None) -> None:
        self.calls = 0
        self.requests: list[dict[str, object]] = []
        self.terminal_status = terminal_status

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls += 1
        self.requests.append(kwargs)
        if self.calls == 1:
            return SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="function_call",
                        name="list_recent_incidents",
                        arguments="{}",
                        call_id="call-1",
                    )
                ],
                output_text="",
            )
        return SimpleNamespace(
            output=[],
            output_text="No recent incident records were returned.",
            status=self.terminal_status,
        )


def test_governed_chat_uses_mocked_responses_function_loop(client) -> None:
    fake_responses = FakeResponses()
    with Session(client.app.state.engine) as session:
        # The fake response requests a bounded registered tool; no network client is used.
        result = governed_chat(
            SimpleNamespace(responses=fake_responses),
            "test-model",
            session,
            "empty-site",
            "What is open?",
            "test-safety-identifier",
        )
    assert result["answer"] == "No recent incident records were returned."
    assert result["tools_used"] == ["list_recent_incidents"]
    assert result["uncertainty_notes"]
    assert fake_responses.requests[0]["safety_identifier"] == "test-safety-identifier"
    second_input = fake_responses.requests[1]["input"]
    assert any(getattr(item, "type", None) == "function_call" for item in second_input)
    assert any(
        isinstance(item, dict)
        and item.get("type") == "function_call_output"
        and item["call_id"] == "call-1"
        for item in second_input
    )


def test_chat_final_deduplicates_and_caps_citations() -> None:
    citations = [{"object_id": str(index), "object_type": "observation"} for index in range(20)]
    citations.extend(
        [
            {"object_id": "0", "object_type": "observation"},
            {"object_id": "i", "object_type": "incident"},
        ]
    )
    result = _final("answer", citations, ["same", "same"], ["tool", "tool"])
    assert len(result["citations"]) == 12
    assert result["citations"][0]["object_type"] == "incident"
    assert result["uncertainty_notes"] == ["same"]
    assert result["tools_used"] == ["tool"]


def test_incomplete_provider_response_adds_uncertainty_note(client) -> None:
    fake = FakeResponses(terminal_status="incomplete")
    with Session(client.app.state.engine) as session:
        result = governed_chat(
            SimpleNamespace(responses=fake),
            "test-model",
            session,
            "empty-site",
            "Question",
            "test-id",
        )
    assert any("incomplete" in note.lower() for note in result["uncertainty_notes"])


def test_chat_forwards_bounded_conversation_history(client) -> None:
    fake = FakeResponses()
    history = [
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
        {"role": "user", "content": "Current question"},
    ]
    with Session(client.app.state.engine) as session:
        governed_chat(
            SimpleNamespace(responses=fake), "test-model", session, "empty-site", history, "test-id"
        )
    assert fake.requests[0]["input"] == history


def test_chat_instructs_provider_to_use_friendly_plant_language(client) -> None:
    fake = FakeResponses()
    with Session(client.app.state.engine) as session:
        governed_chat(
            SimpleNamespace(responses=fake),
            "test-model",
            session,
            "empty-site",
            "What should I review?",
            "test-id",
        )
    instructions = str(fake.requests[0]["instructions"])
    assert "primary-crusher-01 to primary crusher" in instructions
    assert "vibration_mm_s to vibration" in instructions
    assert "Never include internal IDs" in instructions
    assert "explicitly asks for technical details" in instructions
    assert "human-readable Arizona site time" in instructions
    assert "never include ISO 8601 timestamps in prose" in instructions
    assert "Keep citations intact" in instructions
