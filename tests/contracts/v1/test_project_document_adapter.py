from freecad.Corridor_Road.v1.objects import ProjectDocumentAdapter


class _Object:
    def __init__(self, name: str, *, v1_object_type: str = "") -> None:
        self.Name = name
        self.Label = name
        if v1_object_type:
            self.V1ObjectType = v1_object_type

    def addProperty(self, _type_id, name, _group, _description):
        setattr(self, name, None)


class _Document:
    def __init__(self, *, fail_types=()) -> None:
        self.Objects = []
        self.fail_types = set(fail_types)
        self.events = []

    def getObject(self, name):
        return next((obj for obj in self.Objects if obj.Name == name), None)

    def addObject(self, type_id, name):
        if type_id in self.fail_types:
            raise RuntimeError(f"unsupported type: {type_id}")
        obj = _Object(name)
        obj.TypeId = type_id
        self.Objects.append(obj)
        return obj

    def removeObject(self, name):
        self.Objects = [obj for obj in self.Objects if obj.Name != name]
        self.events.append(("remove", name))

    def openTransaction(self, label):
        self.events.append(("open", label))

    def commitTransaction(self):
        self.events.append(("commit", ""))

    def abortTransaction(self):
        self.events.append(("abort", ""))

    def recompute(self):
        self.events.append(("recompute", ""))


def test_project_document_adapter_finds_project_and_stable_object_identity() -> None:
    document = _Document()
    project = _Object("CorridorRoadProject")
    result = _Object("V1Result001", v1_object_type="V1Result")
    document.Objects.extend([project, result])
    adapter = ProjectDocumentAdapter(document)

    assert adapter.project() is project
    assert adapter.find_object(name="V1Result", v1_object_type="V1Result") is result
    assert adapter.find_object(name_prefix="V1Result") is result


def test_project_document_adapter_ensures_object_property_and_value() -> None:
    document = _Document(fail_types={"Part::Feature"})
    adapter = ProjectDocumentAdapter(document)

    obj = adapter.ensure_object("Part::Feature", "V1Preview", fallback_type_id="App::FeaturePython")

    assert obj.TypeId == "App::FeaturePython"
    assert adapter.ensure_property(obj, "App::PropertyString", "V1ObjectType") is True
    assert adapter.set_value(obj, "V1ObjectType", "V1Preview") is True
    assert adapter.ensure_object("Part::Feature", "V1Preview") is obj


def test_project_document_adapter_batches_nested_transaction_and_recompute() -> None:
    document = _Document()
    adapter = ProjectDocumentAdapter(document)

    with adapter.transaction("Outer update", recompute=True):
        with adapter.transaction("Inner update", recompute=True):
            adapter.ensure_object("App::FeaturePython", "V1Result")

    assert document.events == [
        ("open", "Outer update"),
        ("commit", ""),
        ("recompute", ""),
    ]


def test_project_document_adapter_aborts_failed_transaction_without_recompute() -> None:
    document = _Document()
    adapter = ProjectDocumentAdapter(document)

    try:
        with adapter.transaction("Failed update", recompute=True):
            raise RuntimeError("stop")
    except RuntimeError:
        pass

    assert document.events == [("open", "Failed update"), ("abort", "")]


def test_project_document_adapter_removes_only_explicit_stale_results() -> None:
    document = _Document()
    document.Objects.extend(
        [
            _Object("V1PreviewKeep", v1_object_type="V1Preview"),
            _Object("V1PreviewStale", v1_object_type="V1Preview"),
            _Object("V1Source", v1_object_type="V1Source"),
        ]
    )
    adapter = ProjectDocumentAdapter(document)

    removed = adapter.remove_stale_objects(
        keep_names={"V1PreviewKeep"},
        v1_object_types=("V1Preview",),
    )

    assert removed == ["V1PreviewStale"]
    assert {obj.Name for obj in document.Objects} == {"V1PreviewKeep", "V1Source"}
    assert adapter.remove_stale_objects() == []
