from __future__ import annotations

from pathlib import Path
import unittest

from medical_invoice_ocr.models import OcrToken
from medical_invoice_ocr.parser import extract_amounts, parse_invoice


def token(text: str, x1: int, y1: int, x2: int, y2: int, score: float = 0.99) -> OcrToken:
    return OcrToken(text=text, score=score, box=(x1, y1, x2, y2))


class ParserTests(unittest.TestCase):
    def test_extract_printed_and_handwritten_amount(self) -> None:
        self.assertEqual(extract_amounts("2,651.00—2651"), [2651.0, 2651.0])

    def test_parse_and_reconcile_missing_full_deduction(self) -> None:
        tokens = [
            token("交款人：王阿芳", 10, 10, 180, 30),
            token("开票日期：2026-06-09", 300, 10, 520, 30),
            token("项目名称", 10, 50, 100, 70),
            token("诊察费", 10, 100, 80, 120),
            token("22.00", 150, 100, 220, 120),
            token("化验费", 10, 130, 80, 150),
            token("170.00", 150, 130, 230, 150),
            token("(小写)192.00-170.00", 300, 300, 520, 325),
            token("病历号：123", 10, 350, 150, 370),
            token("住院时间：26-6-9至26-6-9", 10, 380, 260, 400),
            token("性别：女", 300, 380, 380, 400),
        ]
        invoice = parse_invoice(Path("IMG_0003.jpg"), tokens)
        self.assertEqual(invoice.patient_name, "王阿芳")
        self.assertEqual(invoice.days, 1)
        self.assertEqual(invoice.fees["化验费"].deduction, 170.0)
        self.assertEqual(invoice.fee_net_total(), 22.0)

    def test_reconcile_decimal_tail(self) -> None:
        tokens = [
            token("交款人：王兴国", 10, 10, 180, 30),
            token("开票日期：2026-03-12", 300, 10, 520, 30),
            token("项目名称", 10, 50, 100, 70),
            token("诊察费", 10, 100, 80, 120),
            token("22.00", 150, 100, 220, 120),
            token("卫生材料费", 10, 130, 110, 150),
            token("63.07-63", 150, 130, 250, 150),
            token("(小写)85.07-63.07", 300, 300, 520, 325),
            token("病历号：123", 10, 350, 150, 370),
            token("住院时间：26-3-12至26-3-12", 10, 380, 280, 400),
            token("性别：女", 300, 380, 380, 400),
        ]
        invoice = parse_invoice(Path("IMG_0005.jpg"), tokens)
        self.assertEqual(invoice.fees["卫生材料费"].deduction, 63.07)
        self.assertEqual(invoice.fee_net_total(), 22.0)


if __name__ == "__main__":
    unittest.main()

