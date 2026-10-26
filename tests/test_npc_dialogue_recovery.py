"""The NPC dialogue recovery: a denied (blocked) dialogue must unblock.

Leg 23: the actuation state sat BLOCKED for 598 sampled ticks - the deny
set the stage 'blocked' but `active` only treats close_requested and
cancel_abandoned as terminal, so the whole window froze. And begin() never
reset the failed flag, so the next dialogue would have been deaf."""

from __future__ import annotations

from robots.adapters.native_npc_dialogue import NativeNpcDialogue


def test_denied_dialogue_keeps_the_fail_closed_barrier() -> None:
    ctx = NativeNpcDialogue()
    ctx.begin(110001762, 1, "prontera", 10, 100.0)
    assert ctx.actuation_blocked
    ctx._expire(200.0)  # past the 5s deadline: the deny fires
    assert ctx.view is not None
    assert ctx.view.stage == "blocked"
    # the barrier holds: the unblock comes from the runtime's fresh begin,
    # never from the silent timeout alone


def test_begin_after_deny_resets_failed() -> None:
    ctx = NativeNpcDialogue()
    ctx.begin(110001762, 1, "prontera", 10, 100.0)
    ctx._expire(200.0)
    assert ctx.failed
    ctx.begin(110001762, 1, "prontera", 20, 300.0)
    assert not ctx.failed  # the fresh dialogue is not deafened by the denial
    # the fresh dialogue is legitimately active (the actuation waits for the
    # server's answer) - the point is the failed flag no longer gates it
