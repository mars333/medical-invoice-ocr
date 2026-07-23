from __future__ import annotations

import argparse
import json

from .pipeline import process_folder


def main() -> None:
    parser = argparse.ArgumentParser(description="医院票据图片批量生成 Excel")
    parser.add_argument("input_dir", help="发票图片目录")
    parser.add_argument("output_dir", help="Excel 输出目录")
    parser.add_argument("--limit", type=int, help="只处理前 N 张，用于测试")
    parser.add_argument("--start-name", help="从指定图片文件名开始")
    args = parser.parse_args()
    summary = process_folder(
        args.input_dir,
        args.output_dir,
        limit=args.limit,
        start_name=args.start_name,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(1 if summary["failed"] else 0)


if __name__ == "__main__":
    main()

