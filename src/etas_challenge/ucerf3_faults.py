"""Parse the admitted UCERF3 fault geometry and loading alternatives."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from etas_challenge.xlsx_reader import read_xlsx_sheet


SLIP_RATE_BRANCHES = (
    "fm3_1_zeng",
    "fm3_1_neokinema",
    "fm3_1_geologic",
    "fm3_1_abm",
    "fm3_2_zeng",
    "fm3_2_neokinema",
    "fm3_2_geologic",
    "fm3_2_abm",
)


@dataclass(frozen=True, slots=True)
class FaultSection:
    section_id: int
    name: str
    in_fault_model_3_1: bool
    in_fault_model_3_2: bool
    dip_degrees: float
    upper_seismogenic_depth_km: float
    lower_seismogenic_depth_km: float
    trace_length_km: float
    trace_lat_lon: tuple[tuple[float, float], ...]
    slip_rate_mm_per_year: dict[str, float | None]
    aseismicity_factor: dict[str, float | None]
    coupling_coefficient: dict[str, float | None]

    def to_payload(self) -> dict:
        return asdict(self)


def _number(value, *, field: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"UCERF3 {field} must be numeric")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"UCERF3 {field} must be at least {minimum}")
    return result


def _optional_number(value, *, field: str) -> float | None:
    if value is None or (isinstance(value, str) and value.strip().lower() == "null"):
        return None
    return _number(value, field=field, minimum=0.0)


def _branch_values(row: list[object], offset: int, *, field: str) -> dict:
    return {
        branch: _optional_number(row[offset + index], field=f"{field}.{branch}")
        for index, branch in enumerate(SLIP_RATE_BRANCHES)
    }


def parse_ucerf3_rows(
    geometry_rows: list[list[object]],
    loading_rows: list[list[object]],
    *,
    expected_sections: int | None = None,
) -> list[FaultSection]:
    """Join the GeometryData and OrigSlipRatesEtc sheets by section ID."""

    if not geometry_rows or geometry_rows[0][:2] != ["Name", "ID"]:
        raise ValueError("unexpected UCERF3 GeometryData header")
    if len(loading_rows) < 2 or loading_rows[1][:2] != [
        "U3 Section Name",
        "U3 Sect ID",
    ]:
        raise ValueError("unexpected UCERF3 OrigSlipRatesEtc header")

    loading_by_id = {}
    for row in loading_rows[2:]:
        if len(row) < 28 or row[1] is None:
            continue
        section_id = int(_number(row[1], field="loading section ID", minimum=0))
        if section_id in loading_by_id:
            raise ValueError(f"duplicate UCERF3 loading section ID: {section_id}")
        loading_by_id[section_id] = row

    sections = []
    seen_ids = set()
    for row in geometry_rows[1:]:
        if len(row) < 12 or row[1] is None:
            continue
        section_id = int(_number(row[1], field="geometry section ID", minimum=0))
        if section_id in seen_ids:
            raise ValueError(f"duplicate UCERF3 geometry section ID: {section_id}")
        seen_ids.add(section_id)
        if section_id not in loading_by_id:
            raise ValueError(f"missing UCERF3 loading section ID: {section_id}")
        loading = loading_by_id[section_id]
        if str(row[0]) != str(loading[0]):
            raise ValueError(f"UCERF3 section name mismatch at ID {section_id}")

        coordinates = [value for value in row[8:] if value is not None]
        if len(coordinates) < 4 or len(coordinates) % 2:
            raise ValueError(f"invalid UCERF3 trace at section ID {section_id}")
        trace = []
        for index in range(0, len(coordinates), 2):
            latitude = _number(coordinates[index], field="trace latitude")
            longitude = _number(coordinates[index + 1], field="trace longitude")
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError(f"invalid UCERF3 trace coordinate at ID {section_id}")
            trace.append((latitude, longitude))

        model_3_1 = bool(row[2])
        model_3_2 = bool(row[3])
        if not model_3_1 and not model_3_2:
            raise ValueError(f"UCERF3 section belongs to no fault model: {section_id}")
        slip = _branch_values(loading, 4, field="slip_rate")
        aseismicity = _branch_values(loading, 12, field="aseismicity")
        coupling = _branch_values(loading, 20, field="coupling")
        for branch, admitted in (
            ("fm3_1", model_3_1),
            ("fm3_2", model_3_2),
        ):
            values = [
                slip[key] for key in SLIP_RATE_BRANCHES if key.startswith(branch)
            ]
            if admitted and all(value is None for value in values):
                raise ValueError(f"missing admitted slip-rate branch at ID {section_id}")
            if not admitted and any(value is not None for value in values):
                raise ValueError(f"unexpected slip-rate branch at ID {section_id}")

        sections.append(
            FaultSection(
                section_id=section_id,
                name=str(row[0]),
                in_fault_model_3_1=model_3_1,
                in_fault_model_3_2=model_3_2,
                dip_degrees=_number(row[4], field="dip", minimum=0.0),
                upper_seismogenic_depth_km=_number(
                    row[5], field="upper seismogenic depth", minimum=0.0
                ),
                lower_seismogenic_depth_km=_number(
                    row[6], field="lower seismogenic depth", minimum=0.0
                ),
                trace_length_km=_number(row[7], field="trace length", minimum=0.0),
                trace_lat_lon=tuple(trace),
                slip_rate_mm_per_year=slip,
                aseismicity_factor=aseismicity,
                coupling_coefficient=coupling,
            )
        )

    if set(loading_by_id) != seen_ids:
        extra = sorted(set(loading_by_id) - seen_ids)
        raise ValueError(f"UCERF3 loading rows without geometry: {extra[:5]}")
    if expected_sections is not None and len(sections) != expected_sections:
        raise ValueError(
            f"expected {expected_sections} UCERF3 sections, found {len(sections)}"
        )
    return sorted(sections, key=lambda section: section.section_id)


def load_ucerf3_fault_sections(
    path: str | Path, *, expected_sections: int = 350
) -> list[FaultSection]:
    return parse_ucerf3_rows(
        read_xlsx_sheet(path, "GeometryData"),
        read_xlsx_sheet(path, "OrigSlipRatesEtc"),
        expected_sections=expected_sections,
    )
