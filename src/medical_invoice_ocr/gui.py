from __future__ import annotations

from queue import Empty, Queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .pipeline import process_folder


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("医院票据图片转 Excel")
        self.geometry("760x520")
        self.minsize(680, 440)
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.queue: Queue[str | tuple[str, dict]] = Queue()
        self._build()
        self.after(100, self._poll)

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="图片文件夹").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.input_var).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="选择", command=self._choose_input).grid(row=1, column=1)
        ttk.Label(frame, text="Excel 输出文件夹").grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=self.output_var).grid(row=3, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="选择", command=self._choose_output).grid(row=3, column=1)
        self.start_button = ttk.Button(frame, text="开始批量生成", command=self._start)
        self.start_button.grid(row=4, column=0, columnspan=2, pady=16)
        self.log = tk.Text(frame, height=18, state="disabled", wrap="word")
        self.log.grid(row=5, column=0, columnspan=2, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(5, weight=1)

    def _choose_input(self) -> None:
        path = filedialog.askdirectory(title="选择发票图片文件夹")
        if path:
            self.input_var.set(path)
            if not self.output_var.get():
                self.output_var.set(path + "/excel")

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择 Excel 输出文件夹")
        if path:
            self.output_var.set(path)

    def _append(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _start(self) -> None:
        if not self.input_var.get() or not self.output_var.get():
            messagebox.showwarning("缺少目录", "请先选择图片文件夹和输出文件夹。")
            return
        self.start_button.configure(state="disabled")
        self._append("开始处理。首次运行会下载 PaddleOCR 模型，请耐心等待……")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            summary = process_folder(
                self.input_var.get(), self.output_var.get(), progress=self.queue.put
            )
            self.queue.put(("done", summary))
        except Exception as exc:  # noqa: BLE001
            self.queue.put(("error", {"error": str(exc)}))

    def _poll(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                if isinstance(item, str):
                    self._append(item)
                elif item[0] == "done":
                    summary = item[1]
                    self._append(
                        f"完成：成功 {summary['exported']}，失败 {summary['failed']}。"
                    )
                    self.start_button.configure(state="normal")
                    messagebox.showinfo("处理完成", "Excel 已生成，请查看输出文件夹。")
                else:
                    self._append("失败：" + item[1]["error"])
                    self.start_button.configure(state="normal")
                    messagebox.showerror("处理失败", item[1]["error"])
        except Empty:
            pass
        self.after(100, self._poll)


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()

