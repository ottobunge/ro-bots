"""A dead transport must be loud: leg 35 froze 7/7 agents silently.

Leg 35 (2026-10-28, 21:30-23:00 UTC) died because the rx thread raised
ValueError('unknown packet 0x0999'). The agent's tick then took the silent
NativeTelemetryUnavailable early-return forever. NOTHING named the cause: the
receipt had no transport field, the runner log printed only the online/decides
summary, and the traces stopped mid-window. The window burned 90 minutes and
three hours of diagnosis before the A/B probe named the frame.

So the runner's receipt must carry the transport's own failure reason, and the
runner's log must say "TRANSPORT DOWN" the first time a reason appears.
"""

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/population_host_runner.py"


def runner_module() -> Any:
    spec = importlib.util.spec_from_file_location("population_host_runner", RUNNER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_error_text_names_the_exception_and_its_message() -> None:
    module = runner_module()
    exc = ValueError("unknown packet 0x0999")
    assert module._error_text(exc) == "ValueError: unknown packet 0x0999"


def test_error_text_is_none_when_the_transport_is_healthy() -> None:
    module = runner_module()
    assert module._error_text(None) is None


def test_error_text_handles_a_bare_exception() -> None:
    module = runner_module()
    assert module._error_text(ConnectionError()) == "ConnectionError"


def test_dispatch_error_summary_counts_by_packet_id() -> None:
    module = runner_module()
    errors = [(0x0999, "boom"), (0x0999, "boom"), (0x00B4, "x")]
    assert module._dispatch_error_summary(errors) == {"0x0999": 2, "0x00B4": 1}


def test_dispatch_error_summary_is_none_when_empty() -> None:
    module = runner_module()
    assert module._dispatch_error_summary(None) is None
    assert module._dispatch_error_summary([]) is None


def test_the_receipt_carries_the_transport_reason() -> None:
    """The receipt's per-agent sample must name the transport's failure."""
    source = RUNNER.read_text()
    assert (
        '"rx_error": _error_text(' in source
    ), "the receipt's per-agent sample must carry the transport failure reason"
    assert '"dispatch_errors": _dispatch_error_summary(' in source


def test_the_runner_log_says_transport_down() -> None:
    """A dead transport must be loud in the log, once per distinct reason."""
    source = RUNNER.read_text()
    assert "TRANSPORT DOWN" in source, "the runner must print the transport failure in its log"
    assert (
        "reported_rx_errors" in source
    ), "the reason must be reported once per distinct value, not every sample"
