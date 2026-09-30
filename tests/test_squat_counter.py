from src.squat_counter import SquatCounter, SquatCounterConfig, SquatState


def feed(counter: SquatCounter, values):
    """Alimenta uma sequência de leituras de profundidade e retorna
    quantos reps novos foram contados no total."""
    total_new = 0
    for value in values:
        if counter.update(value):
            total_new += 1
    return total_new


def test_one_full_squat_is_counted_once():
    counter = SquatCounter()
    # em pé -> desce até o fundo -> volta a esticar
    values = [0.0, 0.05, 0.20, 0.30, 0.38, 0.40, 0.45, 0.40, 0.25, 0.10, 0.05, 0.0]
    new_reps = feed(counter, values)

    assert new_reps == 1
    assert counter.count == 1
    assert counter.state == SquatState.STANDING


def test_three_consecutive_squats():
    counter = SquatCounter()
    one_squat = [0.0, 0.15, 0.30, 0.15, 0.0]
    values = one_squat * 3

    feed(counter, values)

    assert counter.count == 3


def test_partial_squat_that_never_reaches_depth_is_not_counted():
    counter = SquatCounter()
    # desce só até 0.18 (não passa do bottom_threshold=0.20) e volta
    values = [0.0, 0.05, 0.15, 0.18, 0.15, 0.05, 0.0]

    feed(counter, values)

    assert counter.count == 0


def test_noisy_bottom_still_counts_with_default_debounce():
    counter = SquatCounter()
    # ruído leve perto do fundo do movimento (mediapipe "tremendo")
    values = [0.0, 0.12, 0.21, 0.19, 0.22, 0.18, 0.12, 0.0]

    feed(counter, values)

    assert counter.count == 1


def test_min_frames_at_bottom_filters_a_single_frame_spike():
    # exige 3 frames seguidos no fundo para confirmar a profundidade
    config = SquatCounterConfig(min_frames_at_bottom=3)
    counter = SquatCounter(config=config)

    # só 1 frame acima do threshold, depois volta -> não deveria contar
    values = [0.0, 0.12, 0.25, 0.12, 0.0]
    feed(counter, values)
    assert counter.count == 0

    # 3 frames seguidos acima do threshold -> deve contar
    counter.reset()
    values = [0.0, 0.12, 0.25, 0.26, 0.27, 0.12, 0.0]
    feed(counter, values)
    assert counter.count == 1


def test_reset_clears_count_and_state():
    counter = SquatCounter()
    feed(counter, [0.0, 0.15, 0.30, 0.15, 0.0])
    assert counter.count == 1

    counter.reset()
    assert counter.count == 0
    assert counter.state == SquatState.STANDING


def test_is_standing_property():
    counter = SquatCounter()
    assert counter.is_standing

    counter.update(0.20)  # começa a descer
    assert not counter.is_standing
