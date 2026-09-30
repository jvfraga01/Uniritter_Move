import math

from src.geometry import angle_3pts


def test_straight_line_is_180_degrees():
    # a - b - c perfeitamente alinhados e esticados
    a = (0, 0)
    b = (0, 1)
    c = (0, 2)
    assert math.isclose(angle_3pts(a, b, c), 180.0, abs_tol=1e-6)


def test_right_angle_is_90_degrees():
    a = (1, 0)
    b = (0, 0)
    c = (0, 1)
    assert math.isclose(angle_3pts(a, b, c), 90.0, abs_tol=1e-6)


def test_degenerate_points_returns_zero_instead_of_crashing():
    a = (0, 0)
    b = (0, 0)  # ponto duplicado -> vetor de magnitude zero
    c = (1, 1)
    assert angle_3pts(a, b, c) == 0.0
