from src.session import SessionConfig, SessionEvent, SessionManager, SessionState


def test_person_arriving_starts_session_and_zeroes_count():
    session = SessionManager()
    assert session.state == SessionState.WAITING_FOR_PERSON

    event = session.update_presence(True)

    assert event == SessionEvent.STARTED
    assert session.state == SessionState.ACTIVE
    assert session.session_count == 0


def test_no_event_when_presence_does_not_change():
    session = SessionManager()
    assert session.update_presence(False) is None

    session.update_presence(True)
    assert session.update_presence(True) is None


def test_reps_up_to_target_complete_session():
    session = SessionManager(config=SessionConfig(target_reps=3))
    session.update_presence(True)

    assert session.record_rep() is None
    assert session.record_rep() is None
    event = session.record_rep()

    assert event == SessionEvent.COMPLETED
    assert session.state == SessionState.COMPLETE
    assert session.session_count == 3


def test_reps_after_completion_are_ignored():
    session = SessionManager(config=SessionConfig(target_reps=1))
    session.update_presence(True)
    session.record_rep()  # completa a sessão

    assert session.record_rep() is None
    assert session.session_count == 1


def test_rep_without_active_session_is_ignored():
    session = SessionManager()
    assert session.record_rep() is None
    assert session.session_count == 0


def test_person_leaving_resets_after_grace_frames():
    session = SessionManager(config=SessionConfig(target_reps=2, absence_grace_frames=3))
    session.update_presence(True)
    session.record_rep()

    assert session.update_presence(False) is None
    assert session.update_presence(False) is None
    event = session.update_presence(False)

    assert event == SessionEvent.PERSON_LOST
    assert session.state == SessionState.WAITING_FOR_PERSON
    assert session.session_count == 0


def test_person_leaving_after_session_complete_does_not_reset():
    # trava em COMPLETE -- só reset() explícito (botão "Reiniciar sessão")
    # tira daqui, não sair e voltar do quadro.
    session = SessionManager(config=SessionConfig(target_reps=1, absence_grace_frames=1))
    session.update_presence(True)
    session.record_rep()
    assert session.state == SessionState.COMPLETE

    event = session.update_presence(False)
    assert event is None
    assert session.state == SessionState.COMPLETE
    assert session.session_count == 1

    event = session.update_presence(True)
    assert event is None
    assert session.state == SessionState.COMPLETE


def test_reset_exits_complete_state():
    session = SessionManager(config=SessionConfig(target_reps=1))
    session.update_presence(True)
    session.record_rep()
    assert session.state == SessionState.COMPLETE

    session.reset()

    assert session.state == SessionState.WAITING_FOR_PERSON
    assert session.session_count == 0


def test_brief_detection_dropout_does_not_end_session():
    # simula o mediapipe "piscando" (perdendo a pessoa por 2 frames) no
    # meio de um agachamento -- a sessão não pode resetar por causa disso.
    session = SessionManager(config=SessionConfig(target_reps=5, absence_grace_frames=5))
    session.update_presence(True)
    session.record_rep()

    session.update_presence(False)
    session.update_presence(False)
    event = session.update_presence(True)  # pessoa "volta" antes do grace acabar

    assert event is None
    assert session.state == SessionState.ACTIVE
    assert session.session_count == 1  # não foi zerado


def test_set_target_clamps_to_at_least_one():
    session = SessionManager()
    session.set_target(0)
    assert session.config.target_reps == 1

    session.set_target(-5)
    assert session.config.target_reps == 1

    session.set_target(15)
    assert session.config.target_reps == 15


def test_reset_returns_to_waiting_and_zeroes_count():
    session = SessionManager(config=SessionConfig(target_reps=2))
    session.update_presence(True)
    session.record_rep()

    session.reset()

    assert session.state == SessionState.WAITING_FOR_PERSON
    assert session.session_count == 0
