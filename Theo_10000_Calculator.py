import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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

def extract_pdf(pdf_path):

    text = ""

    # อ่าน PDF
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += "\n" + (page.extract_text() or "")

    # =====================================================
    # หา Net Sale
    # =====================================================

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

        line = lines[i]

        code_match = item_code_pattern.fullmatch(
            line.replace(" ", "")
        )

        if not code_match:
            i += 1
            continue

        code = code_match.group(0).upper()

        # -------------------------------------------------
        # เก็บข้อความของ Item
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

            numbers = number_pattern.findall(
                combined
            )

            # มีตัวเลขครบอย่างน้อย 8 ช่อง
            if len(numbers) >= 8:
                break

            j += 1

        block_text = " ".join(block)

        # =================================================
        # ดึงตัวเลข
        # =================================================

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
                # IMPORTANT
                #
                # ใช้ตัวเลขช่องที่ 8 = Theo Usage
                #
                # 1 Opening
                # 2 Purchases
                # 3 Return
                # 4 Transfer In
                # 5 Transfer Out
                # 6 Closing
                # 7 Act. Usage
                # 8 Theo. Usage
                #
                # Python index = 7
                # =================================================

                theo_usage = values[7]

                # -------------------------------------------------
                # Description
                # -------------------------------------------------

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
                # คำนวณผลลัพธ์
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

    return net_sale, clean_rows


# =========================================================
# APPLICATION
# =========================================================

class App:

    def __init__(self, root):

        self.root = root

        self.root.title(APP_TITLE)

        self.root.geometry("1050x650")

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

        ttk.Button(
            bar,
            text="📄 เลือก PDF",
            command=self.open_pdf
        ).pack(
            side="left"
        )

        ttk.Button(
            bar,
            text="📊 Export Excel",
            command=self.export_excel
        ).pack(
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

        try:

            self.net_sale, self.rows = extract_pdf(
                path
            )

            # ล้างข้อมูลเก่า
            for item in self.tree.get_children():
                self.tree.delete(item)

            # แสดงข้อมูลใหม่
            for (
                code,
                description,
                theo_usage,
                result
            ) in self.rows:

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

            self.info.config(
                text=(
                    f"Net Sale: "
                    f"{self.net_sale:,.2f}"
                    f"   |   "
                    f"พบ {len(self.rows)} รายการ"
                )
            )

        except Exception as error:

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
