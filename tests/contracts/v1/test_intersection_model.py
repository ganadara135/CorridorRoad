from freecad.Corridor_Road.v1.models.source.intersection_model import (
    INTERSECTION_KIND_PRESETS,
)


def test_intersection_type_presets_are_user_selectable() -> None:
    assert [str(row["label"]) for row in INTERSECTION_KIND_PRESETS.values()] == ["T Intersection", "Cross Intersection", "Roundabout"]
    assert set(INTERSECTION_KIND_PRESETS) == {"t_intersection", "cross_intersection", "roundabout"}
