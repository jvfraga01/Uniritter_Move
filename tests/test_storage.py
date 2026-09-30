from pathlib import Path

from src.storage import UserState, load_state, save_state


def test_load_state_returns_defaults_when_file_missing(tmp_path):
    path = tmp_path / "nao_existe.json"

    state = load_state(path)

    assert state == UserState(total_squats=0, unlocked_achievements=[])


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "sub" / "state.json"
    original = UserState(total_squats=42, unlocked_achievements=["a", "b"])

    save_state(original, path)
    loaded = load_state(path)

    assert loaded == original
    assert path.exists()
