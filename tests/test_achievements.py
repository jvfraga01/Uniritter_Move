from src.achievements import Achievement, AchievementEngine


def test_unlocks_achievement_when_threshold_is_reached():
    engine = AchievementEngine(achievements=[
        Achievement("first", "Primeiro", "desc", threshold=1),
    ])

    newly = engine.check(total_count=1)

    assert [a.id for a in newly] == ["first"]
    assert "first" in engine.unlocked


def test_does_not_unlock_same_achievement_twice():
    engine = AchievementEngine(achievements=[
        Achievement("first", "Primeiro", "desc", threshold=1),
    ])

    engine.check(total_count=1)
    newly_again = engine.check(total_count=5)

    assert newly_again == []


def test_multiple_thresholds_crossed_at_once():
    engine = AchievementEngine(achievements=[
        Achievement("a", "A", "d", threshold=1),
        Achievement("b", "B", "d", threshold=5),
        Achievement("c", "C", "d", threshold=10),
    ])

    # pulou direto para 10 (ex: app reiniciou e recontou o estado salvo)
    newly = engine.check(total_count=10)

    assert {a.id for a in newly} == {"a", "b", "c"}


def test_resumes_from_previously_unlocked_set():
    engine = AchievementEngine(
        achievements=[
            Achievement("a", "A", "d", threshold=1),
            Achievement("b", "B", "d", threshold=5),
        ],
        unlocked=["a"],
    )

    newly = engine.check(total_count=5)

    assert [a.id for a in newly] == ["b"]
