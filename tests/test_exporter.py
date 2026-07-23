from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import openpyxl

from medical_invoice_ocr.exporter import export_excel
from medical_invoice_ocr.models import FeeValue, ParsedInvoice


class ExporterTests(unittest.TestCase):
    def test_fixed_operator_and_invoice_date(self) -> None:
        invoice = ParsedInvoice(
            source_image=str(Path("IMG_TEST.jpg").resolve()),
            patient_name="测试人",
            gender="女",
            admission_date="20260609",
            discharge_date="20260609",
            days=1,
            receipt_no="123456",
            invoice_date="20260609",
            fees={"诊察费": FeeValue(printed=22, deduction=0)},
            printed_total=22,
            deduction_total=0,
        )
        with tempfile.TemporaryDirectory() as output_dir:
            result = export_excel(invoice, output_dir)
            workbook = openpyxl.load_workbook(result["output_path"], data_only=False)
            sheet = workbook["Sheet1"]
            self.assertEqual(sheet["A2"].value, "2026  06  09")
            self.assertEqual(sheet["C2"].value, "    2026  06  09")
            self.assertEqual(sheet["C2"].alignment.horizontal, "left")
            self.assertEqual(sheet["C3"].value, "（女）")
            self.assertEqual(sheet["C3"].alignment.horizontal, "left")
            self.assertEqual(sheet["D15"].value, "  张鸣")
            self.assertEqual(sheet["D15"].alignment.horizontal, "left")
            self.assertEqual(sheet["E15"].value, "   2026  06  09")
            self.assertAlmostEqual(sheet.page_margins.left, 2.4 / 2.54, delta=0.01)
            self.assertAlmostEqual(sheet.page_margins.right, 0.0, delta=0.01)
            self.assertAlmostEqual(sheet.page_margins.top, 1.5 / 2.54, delta=0.01)
            self.assertAlmostEqual(sheet.page_margins.bottom, 2.5 / 2.54, delta=0.01)
            self.assertAlmostEqual(sheet.page_margins.header, 1.3 / 2.54, delta=0.01)
            self.assertAlmostEqual(sheet.page_margins.footer, 1.3 / 2.54, delta=0.01)
            self.assertEqual(sheet.row_dimensions[11].height, 10.5)


if __name__ == "__main__":
    unittest.main()
