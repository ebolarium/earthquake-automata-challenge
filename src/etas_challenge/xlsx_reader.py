"""Small dependency-free reader for tabular OOXML workbook values."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_REFERENCE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")


def _column_index(reference: str) -> int:
    match = CELL_REFERENCE.fullmatch(reference)
    if match is None:
        raise ValueError(f"invalid XLSX cell reference: {reference}")
    value = 0
    for character in match.group(1):
        value = value * 26 + ord(character) - ord("A") + 1
    return value - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def _sheet_paths(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
    }
    result = {}
    for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
        relationship = sheet.attrib[f"{{{REL_NS}}}id"]
        target = PurePosixPath(targets[relationship])
        path = target if target.is_absolute() else PurePosixPath("xl") / target
        result[sheet.attrib["name"]] = str(path)
    return result


def _cell_value(cell: ET.Element, shared: list[str]):
    value_type = cell.attrib.get("t")
    if value_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t")
        )
    value = cell.find(f"{{{MAIN_NS}}}v")
    if value is None or value.text is None:
        return None
    text = value.text
    if value_type == "s":
        return shared[int(text)]
    if value_type == "b":
        return text == "1"
    if value_type in {"str", "e"}:
        return text
    number = float(text)
    return int(number) if number.is_integer() else number


def read_xlsx_sheet(path: str | Path, sheet_name: str) -> list[list[object]]:
    """Read cached values from one worksheet while preserving empty columns."""

    with zipfile.ZipFile(path) as archive:
        sheets = _sheet_paths(archive)
        if sheet_name not in sheets:
            raise ValueError(f"XLSX sheet not found: {sheet_name}")
        shared = _shared_strings(archive)
        root = ET.fromstring(archive.read(sheets[sheet_name]))

    rows: list[list[object]] = []
    for row in root.findall(f".//{{{MAIN_NS}}}row"):
        values: list[object] = []
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            index = _column_index(cell.attrib["r"])
            if len(values) <= index:
                values.extend([None] * (index + 1 - len(values)))
            values[index] = _cell_value(cell, shared)
        rows.append(values)
    return rows
