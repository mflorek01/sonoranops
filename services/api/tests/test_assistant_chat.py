from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.assistant_chat import governed_chat


class FakeResponses:
    def __init__(self) -> None:
        self.calls = 0
        self.requests: list[dict[str, object]] = []

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
        return SimpleNamespace(output=[], output_text="No recent incident records were returned.")


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
