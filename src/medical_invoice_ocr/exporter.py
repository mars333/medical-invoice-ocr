from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import ParsedInvoice
from .resources import fill_invoice, verify_invoice


def resource_dir() -> Path:
    return Path(__file__).resolve().parent / "resources"


def export_excel(invoice: ParsedInvoice, output_dir: str | Path) -> dict[str, Any]:
    resources = resource_dir()
    template = resources / "template.xlsx"
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result = fill_invoice.fill(template, output, invoice.to_input_dict())
    verify_invoice.verify(Path(result["output_path"]), None, None)
    return result
