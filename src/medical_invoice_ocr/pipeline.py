from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .exporter import export_excel
from .ocr_engine import PaddleOcrEngine
from .parser import parse_invoice


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def list_images(input_dir: str | Path) -> list[Path]:
    root = Path(input_dir)
    return sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )


def process_folder(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    limit: int | None = None,
    start_name: str | None = None,
    progress: Callable[[str], None] = print,
) -> dict:
    images = list_images(input_dir)
    if start_name:
        images = [p for p in images if p.name >= start_name]
    if limit is not None:
        images = images[:limit]
    if not images:
        raise ValueError(f"目录中没有可处理图片: {input_dir}")

    output = Path(output_dir)
    review_dir = output / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    engine = PaddleOcrEngine()
    summary = {"total": len(images), "exported": 0, "failed": 0, "items": []}

    for index, image in enumerate(images, 1):
        progress(f"[{index}/{len(images)}] OCR: {image.name}")
        try:
            tokens = engine.recognize(image)
            invoice = parse_invoice(image, tokens)
            review_path = review_dir / f"{image.stem}.json"
            review_path.write_text(
                json.dumps(invoice.review_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if not invoice.ready_for_export():
                raise ValueError("关键字段缺失，详见 review JSON")
            result = export_excel(invoice, output)
            item = {
                "image": image.name,
                "status": "ok",
                "output": result["output_path"],
                "check_result": result["check_result"],
                "warnings": invoice.warnings,
                "review": str(review_path),
            }
            summary["exported"] += 1
            progress(f"  -> {Path(result['output_path']).name}")
        except Exception as exc:  # noqa: BLE001
            item = {"image": image.name, "status": "failed", "error": str(exc)}
            summary["failed"] += 1
            progress(f"  !! 失败: {exc}")
        summary["items"].append(item)

    summary_path = output / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary

