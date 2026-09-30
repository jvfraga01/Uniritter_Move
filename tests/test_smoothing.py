import pytest

from src.smoothing import MovingAverage


def test_average_of_constant_values_is_the_value_itself():
    ma = MovingAverage(window_size=3)
    assert ma.update(180) == 180
    assert ma.update(180) == 180
    assert ma.update(180) == 180


def test_smooths_a_single_frame_spike():
    ma = MovingAverage(window_size=5)
    for _ in range(5):
        ma.update(180)

    spiked = ma.update(90)  # ruído de 1 frame só (ex: mediapipe "tremeu")

    # a média não deve despencar perto de 90 por causa de 1 frame ruim
    assert spiked > 150


def test_window_size_must_be_positive():
    with pytest.raises(ValueError):
        MovingAverage(window_size=0)


def test_reset_clears_history():
    ma = MovingAverage(window_size=3)
    ma.update(100)
    ma.update(100)

    ma.reset()

    assert ma.update(50) == 50
