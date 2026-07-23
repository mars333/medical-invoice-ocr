import sys


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        del sys.argv[1]
        from medical_invoice_ocr.cli import main as cli_main

        cli_main()
    else:
        from medical_invoice_ocr.gui import main as gui_main

        gui_main()


if __name__ == "__main__":
    main()
