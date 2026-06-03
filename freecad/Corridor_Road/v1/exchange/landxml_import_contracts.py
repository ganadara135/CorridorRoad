"""LandXML import contracts for Parametric Road v1."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LandXMLImportDiagnostic:
    """Structured diagnostic emitted during LandXML scan/import."""

    severity: str
    code: str
    message: str
    context: str = ""


@dataclass(frozen=True)
class LandXMLPointCandidate:
    """Candidate survey point or TIN vertex parsed from LandXML."""

    point_id: str
    x: float
    y: float
    z: float = 0.0
    description: str = ""


@dataclass(frozen=True)
class LandXMLAlignmentElementCandidate:
    """Candidate horizontal geometry element parsed from LandXML."""

    element_id: str
    kind: str
    length: float = 0.0
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LandXMLAlignmentCandidate:
    """Candidate Civil 3D alignment parsed from LandXML."""

    alignment_id: str
    name: str
    start_station: float | None = None
    elements: tuple[LandXMLAlignmentElementCandidate, ...] = ()


@dataclass(frozen=True)
class LandXMLProfilePointCandidate:
    """Candidate profile station/elevation control point."""

    point_id: str
    station: float
    elevation: float
    kind: str = "pvi"


@dataclass(frozen=True)
class LandXMLProfileCandidate:
    """Candidate Civil 3D profile parsed from LandXML."""

    profile_id: str
    name: str
    alignment_id: str = ""
    points: tuple[LandXMLProfilePointCandidate, ...] = ()


@dataclass(frozen=True)
class LandXMLSurfaceCandidate:
    """Candidate Civil 3D TIN surface parsed from LandXML."""

    surface_id: str
    name: str
    points: tuple[LandXMLPointCandidate, ...] = ()
    faces: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class LandXMLImportSummary:
    """Top-level LandXML scan summary."""

    source_path: str = ""
    landxml_version: str = ""
    detected_producer: str = ""
    supported_producer: bool = False
    linear_unit: str = ""
    alignment_count: int = 0
    profile_count: int = 0
    surface_count: int = 0
    cgpoint_count: int = 0


@dataclass(frozen=True)
class LandXMLImportResult:
    """Parsed LandXML candidates plus diagnostics."""

    summary: LandXMLImportSummary
    alignments: tuple[LandXMLAlignmentCandidate, ...] = ()
    profiles: tuple[LandXMLProfileCandidate, ...] = ()
    surfaces: tuple[LandXMLSurfaceCandidate, ...] = ()
    cgpoints: tuple[LandXMLPointCandidate, ...] = ()
    diagnostics: tuple[LandXMLImportDiagnostic, ...] = ()
