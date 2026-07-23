from __future__ import annotations

from datetime import date
import re
from pathlib import Path

from .models import FeeValue, OcrToken, ParsedInvoice


FEE_ALIASES: dict[str, tuple[str, ...]] = {
    "床位费": ("床位费",),
    "诊察费": ("诊察费", "诊查费"),
    "西药费": ("西药费",),
    "中成药": ("中成药费", "中成药"),
    "中草药": ("中草药费", "中草药"),
    "检查费": ("检查费",),
    "治疗费": ("治疗费",),
    "放射费": ("放射费",),
    "手术费": ("手术费",),
    "化验费": ("化验费", "检验费"),
    "输血费": ("输血费",),
    "输氧费": ("输氧费",),
    "放疗费": ("放疗费",),
    "护理费": ("护理费",),
    "伙食费": ("伙食费",),
    "其他": ("其他住院费用", "其他费用", "其他"),
    "卫生材料费": ("卫生材料费", "材料费"),
}

_NUMBER_RE = re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?")


def normalize_text(text: str) -> str:
    table = str.maketrans({
        "，": ",", "。": ".", "－": "-", "—": "-", "–": "-", "~": "-",
        "：": ":", "（": "(", "）": ")", "Ｏ": "0", "o": "0", "O": "0",
        "至": "至",
    })
    return re.sub(r"\s+", "", text.translate(table))


def extract_amounts(text: str) -> list[float]:
    values: list[float] = []
    for match in _NUMBER_RE.finditer(normalize_text(text)):
        whole = match.group(1).replace(",", "")
        decimal = match.group(2)
        raw = whole + ("." + decimal if decimal is not None else "")
        try:
            values.append(round(float(raw), 2))
        except ValueError:
            continue
    return values


def _full_text(tokens: list[OcrToken]) -> str:
    return "\n".join(t.text for t in tokens)


def _match_first(pattern: str, text: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def _parse_date(raw: str) -> str:
    nums = [int(x) for x in re.findall(r"\d+", raw)]
    if len(nums) < 3:
        return ""
    year, month, day = nums[-3:]
    if year < 100:
        year += 2000
    try:
        return date(year, month, day).strftime("%Y%m%d")
    except ValueError:
        return ""


def _display_date(value: str) -> str:
    return f"{value[:4]}  {value[4:6]}  {value[6:]}" if len(value) == 8 else value


def _find_fee_name(text: str) -> tuple[str, str] | None:
    normalized = normalize_text(text)
    for canonical, aliases in FEE_ALIASES.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if normalized.startswith(alias):
                return canonical, alias
    return None


def _row_tokens(anchor: OcrToken, tokens: list[OcrToken]) -> list[OcrToken]:
    # 相邻费用行通常只间隔约一个字高，中心点容差不能过大，否则会把
    # 下一行的印刷金额误配给当前费用。
    tolerance = max(8.0, anchor.height * 0.48)
    return sorted(
        [
            token for token in tokens
            if abs(token.cy - anchor.cy) <= tolerance
            and token.x2 >= anchor.x1
        ],
        key=lambda token: token.x1,
    )


def _parse_fee(anchor: OcrToken, tokens: list[OcrToken], alias: str) -> FeeValue | None:
    row = _row_tokens(anchor, tokens)
    parts: list[str] = []
    scores: list[float] = []
    for token in row:
        if token is not anchor and _find_fee_name(token.text):
            continue
        value = normalize_text(token.text)
        if token is anchor:
            value = value.replace(alias, "", 1)
        if value:
            parts.append(value)
            scores.append(token.score)
    raw = " ".join(parts)
    amounts = extract_amounts(raw)
    if not amounts:
        return None
    printed = amounts[0]
    deduction = amounts[1] if len(amounts) >= 2 else 0.0
    if deduction > printed:
        deduction = 0.0
    return FeeValue(
        printed=printed,
        deduction=deduction,
        confidence=min(scores) if scores else anchor.score,
        raw_text=raw,
    )


def _parse_total(tokens: list[OcrToken]) -> tuple[float | None, float | None, str]:
    anchors = [t for t in tokens if "小写" in normalize_text(t.text)]
    for anchor in anchors:
        row = _row_tokens(anchor, tokens)
        raw = " ".join(t.text for t in row)
        values = extract_amounts(raw)
        if values:
            return values[0], values[1] if len(values) > 1 else None, raw
    return None, None, ""


def _extract_stay_dates(text: str) -> tuple[str, str]:
    normalized = normalize_text(text)
    match = re.search(
        r"住院时间[:：]?([0-9]{2,4}[-/.][0-9]{1,2}[-/.][0-9]{1,2})至"
        r"([0-9]{2,4}[-/.][0-9]{1,2}[-/.][0-9]{1,2})",
        normalized,
    )
    if not match:
        return "", ""
    return _parse_date(match.group(1)), _parse_date(match.group(2))


def _inclusive_days(start: str, end: str) -> int | None:
    if len(start) != 8 or len(end) != 8:
        return None
    try:
        a = date(int(start[:4]), int(start[4:6]), int(start[6:]))
        b = date(int(end[:4]), int(end[4:6]), int(end[6:]))
        return (b - a).days + 1
    except ValueError:
        return None


def _reconcile_missing_deductions(invoice: ParsedInvoice) -> None:
    """Use the independently OCRed total to recover missed handwritten deductions.

    PaddleOCR sometimes reads ``170.00-170`` as only ``170.00``. If the exact
    difference can be explained by one unique subset of currently zero-deduction
    fee amounts, fill that subset and record a review warning.
    """
    if invoice.deduction_total is None:
        return
    current = round(sum(v.deduction for v in invoice.fees.values()), 2)
    gap_cents = round((invoice.deduction_total - current) * 100)
    if gap_cents <= 0:
        return
    # Handwriting may lose only the decimal tail, e.g. ``63.07-63.07`` is read
    # as ``63.07-63``. If exactly one partial deduction explains the gap, it is
    # safe to complete that deduction to the printed amount.
    partial_matches = [
        name for name, value in invoice.fees.items()
        if 0 < value.deduction < value.printed
        and round((value.printed - value.deduction) * 100) == gap_cents
    ]
    if len(partial_matches) == 1:
        name = partial_matches[0]
        invoice.fees[name].deduction = invoice.fees[name].printed
        invoice.warnings.append(f"根据手写扣减合计补全小数尾差：{name}")
        return
    candidates = [
        (name, round(value.printed * 100))
        for name, value in invoice.fees.items()
        if value.deduction == 0 and value.printed > 0 and name != "诊察费"
    ]
    solutions: list[list[str]] = []
    for mask in range(1, 1 << len(candidates)):
        total = 0
        names: list[str] = []
        for index, (name, cents) in enumerate(candidates):
            if mask & (1 << index):
                total += cents
                names.append(name)
        if total == gap_cents:
            solutions.append(names)
    if len(solutions) != 1:
        return
    for name in solutions[0]:
        invoice.fees[name].deduction = invoice.fees[name].printed
    invoice.warnings.append(
        "根据手写扣减合计补全未识别扣减：" + "、".join(solutions[0])
    )


def parse_invoice(image_path: str | Path, tokens: list[OcrToken]) -> ParsedInvoice:
    full = _full_text(tokens)
    normalized = normalize_text(full)
    invoice = ParsedInvoice(source_image=str(Path(image_path).resolve()), ocr_tokens=tokens)

    invoice.patient_name = _match_first(r"(?:^|\n)交款人[:：]([^\n]+)", full)
    invoice.patient_name = re.split(r"\s|票据|校验|开票", invoice.patient_name)[0]
    invoice.invoice_date = _parse_date(_match_first(r"开票日期[:：]?([^\n]+)", full))
    invoice.receipt_no = _match_first(r"(?:病历号|住院号)[:：]?\s*([0-9]+)", full)
    invoice.gender = _match_first(r"性别[:：]?\s*([男女])", full)
    invoice.admission_date, invoice.discharge_date = _extract_stay_dates(full)
    invoice.days = _inclusive_days(invoice.admission_date, invoice.discharge_date)
    invoice.cashier = _match_first(r"收款人[:：]?\s*([^\s\n]+)", full)

    total_anchors = [t for t in tokens if "小写" in normalize_text(t.text)]
    total_y = min((t.cy for t in total_anchors), default=float("inf"))
    table_headers = [t for t in tokens if normalize_text(t.text) == "项目名称"]
    table_y = min((t.cy for t in table_headers), default=0.0)
    seen: set[str] = set()
    for token in tokens:
        if not (table_y < token.cy < total_y):
            continue
        found = _find_fee_name(token.text)
        if not found:
            continue
        canonical, alias = found
        if canonical in seen:
            continue
        fee = _parse_fee(token, tokens, alias)
        if fee is None:
            invoice.warnings.append(f"{canonical}：找到费用名但未识别金额")
            continue
        invoice.fees[canonical] = fee
        seen.add(canonical)
        if fee.confidence < 0.85:
            invoice.warnings.append(f"{canonical}：OCR 置信度较低 {fee.confidence:.2f}")

    printed_total, deduction_total, total_raw = _parse_total(tokens)
    invoice.printed_total = printed_total
    invoice.deduction_total = deduction_total
    if invoice.printed_total is None and invoice.fees:
        invoice.printed_total = round(sum(v.printed for v in invoice.fees.values()), 2)
        invoice.warnings.append("未识别到小写合计，使用费用印刷金额之和")
    if invoice.deduction_total is None and invoice.fees:
        invoice.deduction_total = round(sum(v.deduction for v in invoice.fees.values()), 2)
        invoice.warnings.append("未识别到手写扣减合计，使用各项扣减之和")

    _reconcile_missing_deductions(invoice)

    if invoice.printed_total is not None and invoice.fees:
        fee_printed = round(sum(v.printed for v in invoice.fees.values()), 2)
        if abs(fee_printed - invoice.printed_total) >= 0.01:
            invoice.warnings.append(
                f"印刷费用之和 {fee_printed:.2f} 与小写合计 {invoice.printed_total:.2f} 不一致"
            )
    if invoice.deduction_total is not None and invoice.fees:
        fee_deduction = round(sum(v.deduction for v in invoice.fees.values()), 2)
        if abs(fee_deduction - invoice.deduction_total) >= 0.01:
            invoice.warnings.append(
                f"各项扣减之和 {fee_deduction:.2f} 与手写扣减合计 {invoice.deduction_total:.2f} 不一致"
            )
    if total_raw and len(extract_amounts(total_raw)) < 2:
        invoice.warnings.append(f"合计行只识别到一个金额：{total_raw}")
    if not invoice.patient_name:
        invoice.warnings.append("未识别交款人")
    if not invoice.invoice_date:
        invoice.warnings.append("未识别开票日期")
    if not invoice.gender:
        invoice.warnings.append("未识别性别")
    if not invoice.receipt_no:
        invoice.warnings.append("未识别病历号/住院号")
    if not invoice.fees:
        invoice.warnings.append("未识别任何费用明细")
    return invoice
