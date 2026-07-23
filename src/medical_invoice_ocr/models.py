from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OcrToken:
    text: str
    score: float
    box: tuple[float, float, float, float]

    @property
    def x1(self) -> float:
        return self.box[0]

    @property
    def y1(self) -> float:
        return self.box[1]

    @property
    def x2(self) -> float:
        return self.box[2]

    @property
    def y2(self) -> float:
        return self.box[3]

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def height(self) -> float:
        return max(1.0, self.y2 - self.y1)


@dataclass
class FeeValue:
    printed: float
    deduction: float = 0.0
    confidence: float = 1.0
    raw_text: str = ""


@dataclass
class ParsedInvoice:
    source_image: str
    patient_name: str = ""
    gender: str = ""
    admission_date: str = ""
    discharge_date: str = ""
    days: int | None = None
    receipt_no: str = ""
    invoice_date: str = ""
    fees: dict[str, FeeValue] = field(default_factory=dict)
    printed_total: float | None = None
    deduction_total: float | None = None
    cashier: str = ""
    payment_method: str = ""
    warnings: list[str] = field(default_factory=list)
    ocr_tokens: list[OcrToken] = field(default_factory=list)

    def fee_net_total(self) -> float:
        return round(sum(v.printed - v.deduction for v in self.fees.values()), 2)

    def final_amount(self) -> float | None:
        if self.printed_total is None or self.deduction_total is None:
            return None
        return round(self.printed_total - self.deduction_total, 2)

    def to_input_dict(self) -> dict[str, Any]:
        if not self.patient_name:
            raise ValueError("未识别到交款人姓名")
        if not self.invoice_date:
            raise ValueError("未识别到开票日期")
        if self.printed_total is None:
            raise ValueError("未识别到票据金额合计")
        if self.deduction_total is None:
            raise ValueError("未识别到手写扣减合计")
        patient = {
            "name": self.patient_name,
            "gender": self.gender,
            "admission_date": self.admission_date,
            "discharge_date": self.discharge_date,
            "days": self.days,
            "receipt_no": self.receipt_no,
        }
        return {
            "source_image": self.source_image,
            "patient": patient,
            "invoice_date": self.invoice_date,
            "invoice_date_display": self.invoice_date_display(),
            "fees": {
                name: {"printed": value.printed, "deduction": value.deduction}
                for name, value in self.fees.items()
            },
            "invoice_totals": {
                "printed": self.printed_total,
                "deduction": self.deduction_total,
            },
            "cashier": self.cashier,
            "payment_method": self.payment_method,
        }

    def invoice_date_display(self) -> str:
        d = self.invoice_date
        return f"{d[:4]}  {d[4:6]}  {d[6:]}" if len(d) == 8 else d

    def review_dict(self) -> dict[str, Any]:
        data = self.to_input_dict() if self.ready_for_export() else {
            "source_image": self.source_image,
            "patient_name": self.patient_name,
            "invoice_date": self.invoice_date,
            "fees": {k: asdict(v) for k, v in self.fees.items()},
            "printed_total": self.printed_total,
            "deduction_total": self.deduction_total,
        }
        data["warnings"] = self.warnings
        data["fee_net_total"] = self.fee_net_total()
        data["final_amount"] = self.final_amount()
        data["ocr_tokens"] = [asdict(t) for t in self.ocr_tokens]
        return data

    def ready_for_export(self) -> bool:
        return bool(
            self.patient_name
            and self.invoice_date
            and self.fees
            and self.printed_total is not None
            and self.deduction_total is not None
        )

    @property
    def image_path(self) -> Path:
        return Path(self.source_image)

