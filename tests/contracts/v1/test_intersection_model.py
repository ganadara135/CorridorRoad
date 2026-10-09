from freecad.Corridor_Road.v1.models.source.intersection_model import (
    INTERSECTION_KIND_PRESETS,
    intersection_kind_from_label,
    intersection_preset_labels,
)


def test_intersection_type_presets_are_user_selectable() -> None:
    labels = intersection_preset_labels()

    assert labels == ["T Intersection", "Cross Intersection", "Roundabout"]
    assert intersection_kind_from_label("T Intersection") == "t_intersection"
    assert intersection_kind_from_label("Cross Intersection") == "cross_intersection"
    assert intersection_kind_from_label("Roundabout") == "roundabout"
    assert set(INTERSECTION_KIND_PRESETS) == {"t_intersection", "cross_intersection", "roundabout"}
