from src.backend.agents.graph import _with_stream_status
from src.backend.services.chat_stream import ChatStreamSink, bind_chat_stream


def test_graph_node_emits_progress_before_work() -> None:
    events: list[dict] = []

    def node(state: dict) -> dict:
        events.append({"type": "node", "value": state["value"]})
        return {"done": True}

    wrapped = _with_stream_status("searching", node)
    sink = ChatStreamSink(emit=events.append, is_cancelled=lambda: False)

    with bind_chat_stream(sink):
        result = wrapped({"value": 7})

    assert result == {"done": True}
    assert events == [
        {"type": "status", "stage": "searching"},
        {"type": "node", "value": 7},
    ]
