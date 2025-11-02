from __future__ import annotations

import gradio as gr

from src.ui.live_session_tab import (
    _initial_audio_meter,
    _initial_status,
    _initial_speaker_timeline,
    _start_session,
    _stop_session,
    create_live_session_tab,
)


def test_live_session_tab_scaffolding():
    with gr.Blocks() as demo:
        refs = create_live_session_tab(demo)

    expected_keys = {
        "start_button",
        "stop_button",
        "status",
        "transcript_stream",
        "speaker_timeline",
        "audio_meter",
        "state",
    }
    assert expected_keys.issubset(refs.keys())
    assert "Live capture idle" in refs["status"].value


def test_start_and_stop_state_transitions():
    status, transcript, speakers, meter, state, start_update, stop_update = _start_session(
        "idle",
        "",
        _initial_speaker_timeline(),
    )
    assert "Processing" in status
    assert state == "running"
    assert start_update["interactive"] is False
    assert stop_update["interactive"] is True

    status2, transcript2, speakers2, meter2, state2, start_update2, stop_update2 = _stop_session(
        state,
        transcript,
        speakers,
    )
    assert "Capture stopped" in status2
    assert state2 == "idle"
    assert start_update2["interactive"] is True
    assert stop_update2["interactive"] is False
    assert meter2 == _initial_audio_meter()


def test_stop_without_running_session():
    status, _, _, _, state, start_update, stop_update = _stop_session(
        "idle",
        "",
        _initial_speaker_timeline(),
    )
    assert "not currently running" in status
    assert state == "idle"
    assert start_update["interactive"] is False
    assert stop_update["interactive"] is False
