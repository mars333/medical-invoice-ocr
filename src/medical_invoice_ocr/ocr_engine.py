from __future__ import annotations

import os
from pathlib import Path
import sys

from .models import OcrToken


def _frozen_log(message: str) -> None:
    if not getattr(sys, "frozen", False) or os.environ.get("MEDICAL_INVOICE_DEBUG") != "1":
        return
    try:
        log_path = Path(sys.executable).resolve().parent / "exe_debug.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except OSError:
        pass


class PaddleOcrEngine:
    """Lazy PaddleOCR wrapper. The model is created once for a whole batch."""

    def __init__(self, lang: str = "ch") -> None:
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        _frozen_log("1 importing paddleocr")
        from paddleocr import PaddleOCR
        _frozen_log("2 imported paddleocr")

        model_kwargs: dict[str, str] = {}
        if getattr(sys, "frozen", False):
            model_root = Path(sys.executable).resolve().parent / "models"
            detection = model_root / "PP-OCRv6_medium_det"
            recognition = model_root / "PP-OCRv6_medium_rec"
            if not detection.is_dir() or not recognition.is_dir():
                raise FileNotFoundError(
                    f"EXE 旁缺少 OCR 模型目录：{model_root}。请完整解压分发包后运行。"
                )
            model_kwargs = {
                "text_detection_model_dir": str(detection),
                "text_recognition_model_dir": str(recognition),
            }
            _frozen_log(f"3 model dirs ok: {model_root}")
        _frozen_log("4 creating PaddleOCR")
        self._ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
            **model_kwargs,
        )
        _frozen_log("5 PaddleOCR ready")

    def recognize(self, image_path: str | Path) -> list[OcrToken]:
        _frozen_log(f"6 predict start: {image_path}")
        results = self._ocr.predict(str(image_path))
        _frozen_log("7 predict finished")
        if not results:
            return []
        result = results[0]
        texts = result.get("rec_texts", [])
        scores = result.get("rec_scores", [])
        boxes = result.get("rec_boxes", [])
        tokens: list[OcrToken] = []
        for text, score, box in zip(texts, scores, boxes, strict=False):
            if not str(text).strip():
                continue
            x1, y1, x2, y2 = [float(v) for v in box]
            tokens.append(OcrToken(str(text).strip(), float(score), (x1, y1, x2, y2)))
        return sorted(tokens, key=lambda t: (t.cy, t.x1))
