import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.xlsx_reader import read_xlsx_sheet


WORKBOOK = """<?xml version="1.0"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <sheets><sheet name="Faults" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
RELATIONSHIPS = """<?xml version="1.0"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
SHARED = """<?xml version="1.0"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <si><t>section_id</t></si><si><t>San Test</t></si>
</sst>"""
SHEET = """<?xml version="1.0"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <sheetData>
  <row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1" t="inlineStr"><is><t>slip</t></is></c></row>
  <row r="2"><c r="A2"><v>12</v></c><c r="B2" t="s"><v>1</v></c><c r="C2"><f>1+2</f><v>3.5</v></c></row>
 </sheetData>
</worksheet>"""


class XlsxReaderTests(unittest.TestCase):
    def test_reads_shared_inline_numeric_and_formula_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("xl/workbook.xml", WORKBOOK)
                archive.writestr("xl/_rels/workbook.xml.rels", RELATIONSHIPS)
                archive.writestr("xl/sharedStrings.xml", SHARED)
                archive.writestr("xl/worksheets/sheet1.xml", SHEET)
            self.assertEqual(
                read_xlsx_sheet(path, "Faults"),
                [["section_id", None, "slip"], [12, "San Test", 3.5]],
            )

    def test_rejects_unknown_sheet(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("xl/workbook.xml", WORKBOOK)
                archive.writestr("xl/_rels/workbook.xml.rels", RELATIONSHIPS)
                archive.writestr("xl/worksheets/sheet1.xml", SHEET)
            with self.assertRaises(ValueError):
                read_xlsx_sheet(path, "Missing")


if __name__ == "__main__":
    unittest.main()
