from app.services.llm.base import Action, Interpretation, InterpretContext, Interpreter, InterpreterError


class FakeInterpreter(Interpreter):
    """Returns queued interpretations in order and records what it was asked."""

    def __init__(self):
        self.queue: list[Interpretation | InterpreterError] = []
        self.calls: list[tuple[str, InterpretContext]] = []

    def will_return(self, *actions: dict) -> None:
        self.queue.append(Interpretation(actions=[Action(**action) for action in actions]))

    def will_fail(self, reason: str) -> None:
        self.queue.append(InterpreterError(reason))

    def interpret(self, message: str, context: InterpretContext) -> Interpretation:
        self.calls.append((message, context))
        result = self.queue.pop(0)
        if isinstance(result, InterpreterError):
            raise result
        return result
