"""
Fake model and response data classes — zero external dependencies.

Block and Response mirror the shape of a real LLM SDK response (e.g., Anthropic's
Messages API). FakeModel returns scripted Response objects in sequence, enabling the
harness to run a full init → tool-call → permission-check → audit → exit cycle
without network access or API keys.

Usage:
    from demo.fake_model import Block, Response, FakeModel

    script = [
        Response(
            content=[Block(type="tool_use", name="bash",
                           input={"command": "ls"}, id="call_1")],
            stop_reason="tool_use",
        ),
        Response(
            content=[Block(type="text", text="Done.")],
            stop_reason="end_turn",
        ),
    ]
    model = FakeModel(script)
    response = model(messages)  # returns script[0], then script[1], ...
"""


class Block:
    """A single content block in a model response.

    Matches the structure of Anthropic SDK content blocks:
    - type="tool_use": the model is requesting a tool call
    - type="text": the model is producing text output
    """

    def __init__(self, type, name=None, input=None, text=None, id=None):
        self.type = type        # "tool_use" | "text"
        self.name = name        # tool name (for tool_use blocks)
        self.input = input if input is not None else {}  # tool arguments
        self.text = text        # text content (for text blocks)
        self.id = id            # unique block ID (for correlating results)

    def __repr__(self):
        if self.type == "tool_use":
            return f"Block(type='tool_use', name={self.name!r}, input={self.input!r}, id={self.id!r})"
        return f"Block(type='text', text={self.text!r})"


class Response:
    """A model response containing one or more content blocks.

    stop_reason indicates why the model stopped:
    - "tool_use": the model wants to call tools (agent loop should continue)
    - "end_turn": the model is done (agent loop should exit)
    """

    def __init__(self, content, stop_reason):
        self.content = content          # list[Block]
        self.stop_reason = stop_reason  # "tool_use" | "end_turn"

    def __repr__(self):
        return f"Response(content={self.content!r}, stop_reason={self.stop_reason!r})"


class FakeModel:
    """A scripted model that returns pre-determined Response objects in sequence.

    Takes a list of Response objects at construction time and returns them
    one by one on each call. After exhausting the script, returns an end_turn
    Response with a "script exhausted" message.

    This allows the agent loop to run a complete demo without any network
    access, API keys, or external dependencies.
    """

    def __init__(self, responses):
        """
        Args:
            responses: list[Response] — scripted responses returned in order.
        """
        self._responses = list(responses)
        self._index = 0

    def __call__(self, messages):
        """Return the next scripted response, ignoring messages.

        Args:
            messages: conversation history (ignored — responses are scripted).

        Returns:
            Response — the next response in the script.
        """
        if self._index < len(self._responses):
            resp = self._responses[self._index]
            self._index += 1
            return resp
        # Fallback: signal end_turn if script is exhausted
        return Response(
            content=[Block(type="text", text="[fake model] script exhausted")],
            stop_reason="end_turn",
        )

    def reset(self):
        """Reset the model to replay the script from the beginning."""
        self._index = 0
