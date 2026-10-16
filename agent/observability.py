"""Arize AX tracing via OpenTelemetry/OpenInference. No-op when keys are absent."""
from __future__ import annotations

import os

os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
from contextlib import contextmanager

_tracer = None
PROJECT = "proofloop"


def init() -> bool:
    global _tracer
    if not (os.environ.get("ARIZE_API_KEY") and os.environ.get("ARIZE_SPACE_ID")):
        return False
    from arize.otel import register

    tp = register(space_id=os.environ["ARIZE_SPACE_ID"], api_key=os.environ["ARIZE_API_KEY"],
                  project_name=PROJECT, verbose=False)
    for mod, cls in (("openinference.instrumentation.openai", "OpenAIInstrumentor"),
                     ("openinference.instrumentation.anthropic", "AnthropicInstrumentor"),
                     ("openinference.instrumentation.bedrock", "BedrockInstrumentor")):
        try:
            getattr(__import__(mod, fromlist=[cls]), cls)().instrument(tracer_provider=tp)
        except Exception:
            pass
    _tracer = tp.get_tracer("proofloop")
    return True


@contextmanager
def span(name: str, kind: str = "CHAIN", **attrs):
    if _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as s:
        s.set_attribute("openinference.span.kind", kind)
        for k, v in attrs.items():
            s.set_attribute(k, v)
        yield s


def set_attrs(s, **attrs) -> None:
    if s is not None:
        for k, v in attrs.items():
            s.set_attribute(k, v)


def finish(s, input_value: str, output_value: str, ok: bool) -> None:
    """Fill the Input/Output columns and status shown in the Arize trace list."""
    if s is None:
        return
    from opentelemetry.trace import Status, StatusCode

    s.set_attribute("input.value", input_value)
    s.set_attribute("output.value", output_value)
    s.set_status(Status(StatusCode.OK if ok else StatusCode.ERROR))


def flush() -> None:
    if _tracer is not None:
        from opentelemetry import trace

        tp = trace.get_tracer_provider()
        if hasattr(tp, "force_flush"):
            tp.force_flush()
