from Core.avatar_activity_state import (
    discover_outfit_catalog,
    discover_rigged_model,
    infer_avatar_action,
    infer_form,
)


def test_activity_actions() -> None:
    assert infer_avatar_action("read a fashion magazine") == "read_magazine"
    assert infer_avatar_action("read a history book") == "read_book"
    assert infer_avatar_action("work on code at the computer") == "use_computer"
    assert infer_avatar_action("patrol Paris") == "walk"


def test_activity_forms() -> None:
    assert infer_form("patrol Paris", "Ladybug") == "hero"
    assert infer_form("get ready for bed", "Marinette pajamas") == "sleepwear"
    assert infer_form("write in a diary", "Marinette") == "civilian"


def test_missing_optional_avatar_assets_are_safe() -> None:
    assert discover_rigged_model("candidate_that_does_not_exist") is None
    assert discover_outfit_catalog("candidate_that_does_not_exist") is None
