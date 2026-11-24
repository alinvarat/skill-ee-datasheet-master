"""CLI regression checks using synthetic PDFs; no user files or network."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import pymupdf as fitz
except ImportError:
    import fitz

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "pdf_tools.py"


class PDFToolsCLI(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *map(str, args)], text=True, capture_output=True, timeout=20)

    def test_help_without_pdf(self):
        result = self.run_tool("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("search_table", result.stdout)

    def test_missing_pdf_and_invalid_page_are_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.pdf"
            result = self.run_tool("info", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error", json.loads(result.stdout))
            doc = fitz.open()
            doc.new_page()
            doc.save(path)
            doc.close()
            result = self.run_tool("text", path, 0)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("out of range", result.stdout)

    def test_extract_table_while_document_is_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "table.pdf"
            doc = fitz.open()
            page = doc.new_page()
            for y in (60, 90, 120):
                page.draw_line((60, y), (340, y))
            for x in (60, 220, 340):
                page.draw_line((x, 60), (x, 120))
            for point, text in [((70, 80), "Parameter"), ((230, 80), "Typical"), ((70, 110), "Supply voltage"), ((230, 110), "3300 mV")]:
                page.insert_text(point, text)
            doc.save(path)
            doc.close()
            result = self.run_tool("tables", path, 1)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rows = json.loads(result.stdout)
            cells = [cell for table in rows for row in table for cell in row]
            self.assertIn("Parameter", cells)
            self.assertIn("Supply voltage", cells)
            self.assertIn("3300 mV", cells)


if __name__ == "__main__":
    unittest.main()
