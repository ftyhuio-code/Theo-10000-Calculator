import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import pdfplumber


APP_TITLE = "Theo Usage Calculator"


# =========================================================
# NUMBER
# =========================================================

def num(value):
    value = str(value).replace(",", "").strip()

    if not value:
        return 0.0

    if value.startswith("(") and value.endswith(")"):
        return -float(value[1:-1])

    return float(value)


# =========================================================
# EXTRACT PDF
# =========================================================

def extract_pdf(pdf_path, status_callback=None):

    text_parts = []

    # =====================================================
    # อ่าน PDF
    # =====================================================

    with pdfplumber.open(pdf_path) as pdf:

        total_pages = len(pdf.pages)

        for page_number, page in enumerate(pdf.pages, start=1):

            page_text = page.extract_text() or ""

            if page_text:
                text_parts.append(page_text)

            if status_callback:
                status_callback(
                    f"กำลังอ่าน PDF... หน้า {page_number}/{total_pages}"
                )

    text = "\n".join(text_parts)

    if not text.strip():
        raise ValueError("ไม่สามารถอ่านข้อความจาก PDF ได้")

    # =====================================================
    # หา Net Sale
    # =====================================================

    if status_callback:
        status_callback("กำลังค้นหา Net Sale...")

    net_sale_match = re.search(
        r"Net\s+Sale\s+([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if not net_sale_match:
        raise ValueError("ไม่พบ Net Sale ใน PDF")

    net_sale = num(net_sale_match.group(1))

    if net_sale == 0:
        raise ValueError("Net Sale เป็น 0 ไม่สามารถคำนวณได้")

    # =====================================================
    # แยกบรรทัด
    # =====================================================

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # =====================================================
    # Pattern
    # =====================================================

    item_code_pattern = re.compile(
        r"TH[A-Z0-9]+",
        re.IGNORECASE
    )

    number_pattern = re.compile(
        r"\(?-?\d[\d,]*(?:\.\d+)?\)?"
    )

    rows = []

    i = 0

    # =====================================================
    # อ่าน Item
    # =====================================================

    while i < len(lines):

        if status_callback and i % 20 == 0:
            status_callback(
                f"กำลังประมวลผลข้อมูล... {i}/{len(lines)}"
            )

        line = lines[i]

        code_match = item_code_pattern.fullmatch(
            line.replace(" ", "")
        )

        if not code_match:
            i += 1
            continue

        code = code_match.group(0).upper()

        # -------------------------------------------------
        # เก็บข้อมูลของ Item
        # -------------------------------------------------

        block = []

        j = i + 1

        while j < len(lines):

            next_line = lines[j]

            # Item ถัดไป
            if item_code_pattern.fullmatch(
                next_line.replace(" ", "")
            ):
                break

            # ส่วนสรุป
            if next_line.startswith(
                (
                    "Sub Total:",
                    "Item Group:",
                    "Total All Item Groups",
                    "QSA -"
                )
            ):
                break

            block.append(next_line)

            combined = " ".join(block)

            number_strings = number_pattern.findall(
                combined
            )

            # =================================================
            # เมื่อมีตัวเลขครบ 8 ช่อง
            # =================================================

            if len(number_strings) >= 8:
                break

            j += 1

        block_text = " ".join(block)

        # =====================================================
        # ดึงตัวเลข
        # =====================================================

        number_strings = number_pattern.findall(
            block_text
        )

        if len(number_strings) >= 8:

            try:

                values = [
                    num(x)
                    for x in number_strings
                ]

                # =================================================
                # Theo Usage
                #
                # ช่องที่ 8
                # Python index = 7
                #
                # 1 Opening
                # 2 Purchases
                # 3 Return
                # 4 Transfer In
                # 5 Transfer Out
                # 6 Closing
                # 7 Act. Usage
                # 8 Theo. Usage
                # =================================================

                theo_usage = values[7]

                # =================================================
                # Description
                # =================================================

                first_number = number_pattern.search(
                    block_text
                )

                if first_number:

                    description = block_text[
                        :first_number.start()
                    ].strip()

                else:

                    description = block_text.strip()

                description = re.sub(
                    r"\s+",
                    " ",
                    description
                )

                if not description:
                    i = max(i + 1, j)
                    continue

                # =================================================
                # คำนวณ
                #
                # Theo Usage × 10,000 ÷ Net Sale
                # =================================================

                result = (
                    theo_usage * 10000
                ) / net_sale

                rows.append(
                    (
                        code,
                        description,
                        theo_usage,
                        result
                    )
                )

            except (
                ValueError,
                IndexError,
                ZeroDivisionError
            ):
                pass

        i = max(i + 1, j)

    # =====================================================
    # ลบข้อมูลซ้ำ
    # =====================================================

    if status_callback:
        status_callback("กำลังตรวจสอบและลบข้อมูลซ้ำ...")

    clean_rows = []

    seen = set()

    for row in rows:

        code = row[0]
        theo_usage = row[2]

        key = (
            code,
            round(theo_usage, 6)
        )

        if key in seen:
            continue

        seen.add(key)

        if theo_usage >= 0:
            clean_rows.append(row)

    if status_callback:
        status_callback(
            f"ประมวลผลเสร็จแล้ว พบ {len(clean_rows)} รายการ"
        )

    return net_sale, clean_rows


# =========================================================
# APPLICATION
# =========================================================

class App:

    def __init__(self, root):

        self.root = root

        self.root.title(APP_TITLE)

        self.root.geometry(
            "1050x650"
        )

        self.root.minsize(
            850,
            550
        )

        self.rows = []

        self.net_sale = 0

        # =================================================
        # TOP
        # =================================================

        top = ttk.Frame(
            root,
            padding=12
        )

        top.pack(
            fill="x"
        )

        ttk.Label(
            top,
            text=APP_TITLE,
            font=(
                "Segoe UI",
                18,
                "bold"
            )
        ).pack(
            anchor="w"
        )

        ttk.Label(
            top,
            text=(
                "Theo Usage × 10,000 ÷ Net Sale"
            )
        ).pack(
            anchor="w",
            pady=(4, 10)
        )

        # =================================================
        # BUTTON BAR
        # =================================================

        bar = ttk.Frame(top)

        bar.pack(
            fill="x"
        )

        self.open_button = ttk.Button(
            bar,
            text="📄 เลือก PDF",
            command=self.open_pdf
        )

        self.open_button.pack(
            side="left"
        )

        self.export_button = ttk.Button(
            bar,
            text="📊 Export Excel",
            command=self.export_excel
        )

        self.export_button.pack(
            side="left",
            padx=8
        )

        self.info = ttk.Label(
            bar,
            text="ยังไม่ได้เลือกไฟล์"
        )

        self.info.pack(
            side="left",
            padx=8
        )

        # =================================================
        # TABLE
        # =================================================

        frame = ttk.Frame(
            root,
            padding=(
                12,
                0,
                12,
                12
            )
        )

        frame.pack(
            fill="both",
            expand=True
        )

        columns = (
            "code",
            "desc",
            "theo",
            "result"
        )

        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings"
        )

        # =================================================
        # HEADERS
        # =================================================

        self.tree.heading(
            "code",
            text="Item Code"
        )

        self.tree.heading(
            "desc",
            text="Description"
        )

        self.tree.heading(
            "theo",
            text="Theo Usage"
        )

        self.tree.heading(
            "result",
            text="ผลลัพธ์"
        )

        # =================================================
        # COLUMN WIDTH
        # =================================================

        self.tree.column(
            "code",
            width=130,
            anchor="w"
        )

        self.tree.column(
            "desc",
            width=500,
            anchor="w"
        )

        self.tree.column(
            "theo",
            width=150,
            anchor="e"
        )

        self.tree.column(
            "result",
            width=180,
            anchor="e"
        )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        # =================================================
        # SCROLLBAR
        # =================================================

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.tree.yview
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        # =================================================
        # LOADING WINDOW
        # =================================================

        self.loading_window = None
        self.loading_label = None
        self.progress = None

    # =====================================================
    # SHOW LOADING
    # =====================================================

    def show_loading(self):

        if self.loading_window is not None:
            return

        self.loading_window = tk.Toplevel(
            self.root
        )

        self.loading_window.title(
            "กำลังประมวลผล"
        )

        self.loading_window.geometry(
            "420x170"
        )

        self.loading_window.resizable(
            False,
            False
        )

        # ป้องกันปิดหน้าต่างระหว่างทำงาน
        self.loading_window.protocol(
            "WM_DELETE_WINDOW",
            lambda: None
        )

        # อยู่ด้านหน้า
        self.loading_window.transient(
            self.root
        )

        self.loading_window.grab_set()

        container = ttk.Frame(
            self.loading_window,
            padding=20
        )

        container.pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            container,
            text="กำลังประมวลผล PDF",
            font=(
                "Segoe UI",
                14,
                "bold"
            )
        ).pack(
            pady=(0, 12)
        )

        self.loading_label = ttk.Label(
            container,
            text="กำลังเริ่มต้น..."
        )

        self.loading_label.pack(
            pady=(0, 12)
        )

        self.progress = ttk.Progressbar(
            container,
            mode="indeterminate",
            length=350
        )

        self.progress.pack()

        self.progress.start(10)

        self.root.update_idletasks()

        # จัดกลางหน้าจอ
        self.loading_window.update_idletasks()

        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()

        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()

        win_w = self.loading_window.winfo_width()
        win_h = self.loading_window.winfo_height()

        x = root_x + (root_w - win_w) // 2
        y = root_y + (root_h - win_h) // 2

        self.loading_window.geometry(
            f"+{x}+{y}"
        )

    # =====================================================
    # UPDATE LOADING
    # =====================================================

    def update_loading(self, message):

        self.root.after(
            0,
            lambda: self._update_loading_text(
                message
            )
        )

    def _update_loading_text(self, message):

        if self.loading_label:

            self.loading_label.config(
                text=message
            )

    # =====================================================
    # HIDE LOADING
    # =====================================================

    def hide_loading(self):

        if self.loading_window:

            try:

                if self.progress:
                    self.progress.stop()

                self.loading_window.grab_release()

                self.loading_window.destroy()

            except tk.TclError:
                pass

        self.loading_window = None
        self.loading_label = None
        self.progress = None

    # =====================================================
    # OPEN PDF
    # =====================================================

    def open_pdf(self):

        path = filedialog.askopenfilename(
            title="เลือก Inventory Activity Standard Report",
            filetypes=[
                (
                    "PDF files",
                    "*.pdf"
                ),
                (
                    "All files",
                    "*.*"
                )
            ]
        )

        if not path:
            return

        # =================================================
        # ล็อกปุ่ม
        # =================================================

        self.open_button.config(
            state="disabled"
        )

        self.export_button.config(
            state="disabled"
        )

        self.info.config(
            text="กำลังประมวลผล..."
        )

        self.show_loading()

        # =================================================
        # Thread
        # =================================================

        thread = threading.Thread(
            target=self.process_pdf,
            args=(path,),
            daemon=True
        )

        thread.start()

    # =====================================================
    # PROCESS PDF
    # =====================================================

    def process_pdf(self, path):

        try:

            net_sale, rows = extract_pdf(
                path,
                status_callback=self.update_loading
            )

            self.root.after(
                0,
                lambda: self.display_results(
                    net_sale,
                    rows
                )
            )

        except Exception as error:

            self.root.after(
                0,
                lambda: self.pdf_error(
                    error
                )
            )

    # =====================================================
    # DISPLAY RESULTS
    # =====================================================

    def display_results(
        self,
        net_sale,
        rows
    ):

        self.net_sale = net_sale

        self.rows = rows

        # =================================================
        # ล้างข้อมูลเดิม
        # =================================================

        for item in self.tree.get_children():

            self.tree.delete(item)

        # =================================================
        # แสดงข้อมูล
        # =================================================

        for (
            code,
            description,
            theo_usage,
            result
        ) in rows:

            self.tree.insert(
                "",
                "end",
                values=(
                    code,
                    description,
                    f"{theo_usage:,.2f}",
                    f"{result:,.2f}"
                )
            )

        # =================================================
        # Info
        # =================================================

        self.info.config(
            text=(
                f"Net Sale: "
                f"{self.net_sale:,.2f}"
                f"   |   "
                f"พบ {len(self.rows)} รายการ"
            )
        )

        self.open_button.config(
            state="normal"
        )

        self.export_button.config(
            state="normal" if self.rows else "disabled"
        )

        self.hide_loading()

    # =====================================================
    # PDF ERROR
    # =====================================================

    def pdf_error(self, error):

        self.hide_loading()

        self.open_button.config(
            state="normal"
        )

        self.export_button.config(
            state="normal" if self.rows else "disabled"
        )

        self.info.config(
            text="อ่าน PDF ไม่สำเร็จ"
        )

        messagebox.showerror(
            "อ่าน PDF ไม่สำเร็จ",
            str(error)
        )

    # =====================================================
    # EXPORT EXCEL
    # =====================================================

    def export_excel(self):

        if not self.rows:

            messagebox.showwarning(
                "ยังไม่มีข้อมูล",
                "กรุณาเลือก PDF ก่อน"
            )

            return

        try:

            import pandas as pd

            path = filedialog.asksaveasfilename(
                title="บันทึกผลลัพธ์",
                defaultextension=".xlsx",
                filetypes=[
                    (
                        "Excel Workbook",
                        "*.xlsx"
                    )
                ],
                initialfile="Theo_10000_Result.xlsx"
            )

            if not path:
                return

            data = []

            for (
                code,
                description,
                theo_usage,
                result
            ) in self.rows:

                data.append(
                    {
                        "Item Code": code,
                        "Description": description,
                        "Theo Usage": theo_usage,
                        "ผลลัพธ์": result
                    }
                )

            df = pd.DataFrame(data)

            df.to_excel(
                path,
                index=False
            )

            messagebox.showinfo(
                "สำเร็จ",
                "บันทึกไฟล์เรียบร้อยแล้ว\n\n"
                + path
            )

        except Exception as error:

            messagebox.showerror(
                "Export ไม่สำเร็จ",
                str(error)
            )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    try:
        root.iconname(APP_TITLE)
    except Exception:
        pass

    app = App(root)

    root.mainloop()
