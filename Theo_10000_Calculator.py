import re
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pdfplumber

APP_TITLE = "Theo Usage Calculator"


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def num(value):
    """แปลงข้อความตัวเลข (รองรับวงเล็บลบ และ จุลภาค) เป็น float"""
    value = str(value).replace(",", "").strip()
    if not value:
        return 0.0
    if value.startswith("(") and value.endswith(")"):
        return -float(value[1:-1])
    return float(value)


def extract_pdf(pdf_path):
    text = ""

    # 1. อ่านข้อความทั้งหมดจาก PDF
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += "\n" + page_text

    # 2. ค้นหา Net Sale
    net_sale_match = re.search(r"Net\s+Sale\s+([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
    if not net_sale_match:
        raise ValueError("ไม่พบข้อมูล Net Sale ในไฟล์ PDF นี้")

    net_sale = num(net_sale_match.group(1))
    if net_sale == 0:
        raise ValueError("Net Sale มีค่าเป็น 0 ไม่สามารถคำนวณได้")

    # 3. เตรียม Patterns
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    item_code_pattern = re.compile(r"TH[A-Z0-9]+", re.IGNORECASE)
    number_pattern = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")

    rows = []
    i = 0
    total_lines = len(lines)

    # 4. วนลูปอ่านข้อมูลสินค้า
    while i < total_lines:
        line = lines[i]
        code_match = item_code_pattern.fullmatch(line.replace(" ", ""))

        if not code_match:
            i += 1
            continue

        code = code_match.group(0).upper()
        block = []
        j = i + 1

        # รวบรวมบรรทัดข้อความของ Item จนกว่าจะพบ Item ถัดไป หรือคำสรุป
        while j < total_lines:
            next_line = lines[j]
            
            if item_code_pattern.fullmatch(next_line.replace(" ", "")) or next_line.startswith(
                ("Sub Total:", "Item Group:", "Total All Item Groups", "QSA -")
            ):
                break

            block.append(next_line)
            combined = " ".join(block)
            matches = list(number_pattern.finditer(combined))

            # ต้องพบตัวเลขอย่างน้อย 9 ชุด (คอลัมน์มาตรฐานของรายงาน)
            if len(matches) >= 9:
                j += 1
                break

            j += 1

        block_text = " ".join(block)
        matches = list(number_pattern.finditer(block_text))

        if len(matches) >= 9:
            try:
                # เลือก 9 ตัวเลขสุดท้ายเสมอ (ตัดตัวเลขที่อาจปนอยู่ในชื่อสินค้าออก)
                val_matches = matches[-9:]
                values = [num(m.group(0)) for m in val_matches]

                # Index 8 คือ Theo. Usage
                theo_usage = values[8]

                # Description คือข้อความก่อนหน้าตัวเลขคอลัมน์แรก
                first_val_start = val_matches[0].start()
                desc = block_text[:first_val_start].strip()
                desc = re.sub(r"\s+", " ", desc)

                if desc:
                    # คำนวณสูตร: Theo Usage × 10,000 ÷ Net Sale
                    theo_10000 = (theo_usage * 10000) / net_sale
                    rows.append((code, desc, theo_usage, theo_10000))

            except (ValueError, IndexError, ZeroDivisionError):
                pass

        i = max(i + 1, j)

    # 5. กรองข้อมูลซ้ำและค่า Theo Usage ที่ติดลบ
    clean_rows = []
    seen = set()

    for row in rows:
        code, desc, theo, result = row
        key = (code, round(theo, 6))

        if key not in seen and theo >= 0:
            seen.add(key)
            clean_rows.append(row)

    return net_sale, clean_rows


# =========================================================
# APPLICATION GUI
# =========================================================

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1100x650")
        self.root.minsize(850, 500)

        self.rows = []
        self.net_sale = 0.0

        # Style
        style = ttk.Style()
        style.theme_use("clam")

        # Top Frame
        top = ttk.Frame(root, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text=APP_TITLE, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            top, 
            text="คำนวณ Theo Usage × 10,000 ÷ Net Sale",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 10))

        # Button Bar
        bar = ttk.Frame(top)
        bar.pack(fill="x")

        ttk.Button(bar, text="📄 เลือก PDF", command=self.open_pdf).pack(side="left")
        ttk.Button(bar, text="📊 Export Excel", command=self.export_excel).pack(side="left", padx=8)

        self.info = ttk.Label(bar, text="ยังไม่ได้เลือกไฟล์", font=("Segoe UI", 10, "italic"))
        self.info.pack(side="left", padx=8)

        # Table Frame
        frame = ttk.Frame(root, padding=(12, 0, 12, 12))
        frame.pack(fill="both", expand=True)

        # คอลัมน์ที่แสดง (ตัด Act. Usage ออกแล้ว)
        columns = ("code", "desc", "theo", "result")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")

        self.tree.heading("code", text="Item Code")
        self.tree.heading("desc", text="Description")
        self.tree.heading("theo", text="Theo. Usage")
        self.tree.heading("result", text="Theo × 10,000 ÷ Net Sale")

        self.tree.column("code", width=130, anchor="w")
        self.tree.column("desc", width=450, anchor="w")
        self.tree.column("theo", width=150, anchor="e")
        self.tree.column("result", width=240, anchor="e")

        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def open_pdf(self):
        path = filedialog.askopenfilename(
            title="เลือก Inventory Activity Standard Report",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.net_sale, self.rows = extract_pdf(path)

            # ล้างข้อมูลเดิมในตาราง
            for item in self.tree.get_children():
                self.tree.delete(item)

            # แสดงผลลัพธ์ใหม่
            for code, desc, theo, result in self.rows:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        code,
                        desc,
                        f"{theo:,.2f}",
                        f"{result:,.4f}"  # แสดงผลลัพธ์เป็นทศนิยม 4 ตำแหน่ง
                    )
                )

            self.info.config(
                text=f"Net Sale: {self.net_sale:,.2f}   |   พบข้อมูลสำเร็จ {len(self.rows)} รายการ"
            )

        except Exception as error:
            messagebox.showerror("อ่าน PDF ไม่สำเร็จ", str(error))

    def export_excel(self):
        if not self.rows:
            messagebox.showwarning("ยังไม่มีข้อมูล", "กรุณาเลือกไฟล์ PDF และประมวลผลก่อน")
            return

        path = filedialog.asksaveasfilename(
            title="บันทึกผลลัพธ์",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"), ("CSV File", "*.csv")],
            initialfile="Theo_10000_Result.xlsx"
        )
        if not path:
            return

        try:
            # พยายาม Export ด้วย pandas ก่อน หากเครื่องผู้ใช้ไม่มีจะสลับไปใช้ csv อัตโนมัติ
            try:
                import pandas as pd
                data = [
                    {
                        "Item Code": code,
                        "Description": desc,
                        "Theo. Usage": theo,
                        "Theo × 10,000 ÷ Net Sale": result
                    }
                    for code, desc, theo, result in self.rows
                ]
                df = pd.DataFrame(data)
                df.to_excel(path, index=False)
            except ImportError:
                if not path.endswith('.csv'):
                    path = path.rsplit('.', 1)[0] + '.csv'
                with open(path, mode='w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Item Code", "Description", "Theo. Usage", "Theo × 10,000 ÷ Net Sale"])
                    for row in self.rows:
                        writer.writerow(row)

            messagebox.showinfo("สำเร็จ", f"บันทึกไฟล์เรียบร้อยแล้ว:\n{path}")

        except Exception as error:
            messagebox.showerror("Export ไม่สำเร็จ", str(error))


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
        while j < len(lines):

            next_line = lines[j]

            # เจอ Item ถัดไป
            if item_code_pattern.fullmatch(
                next_line.replace(" ", "")
            ):
                break

            # เจอส่วนสรุป
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

            # มีตัวเลขอย่างน้อย 9 ตัว
            # จึงสามารถอ่าน Theo Usage ที่ values[8] ได้
            if len(numbers) >= 9:
                break

            j += 1

        block_text = " ".join(block)

        # =================================================
        # ดึงตัวเลข
        # =================================================

        number_strings = number_pattern.findall(
            block_text
        )

        if len(number_strings) >= 9:

            try:

                values = [
                    num(x)
                    for x in number_strings
                ]

                # =================================================
                # โครงสร้างข้อมูล
                #
                # 0 = Opening
                # 1 = Purchases
                # 2 = Return
                # 3 = Transfer In
                # 4 = Transfer Out
                # 5 = Closing
                # 6 = Act. Usage
                # 7 = ค่าอื่น
                # 8 = Theo. Usage
                #
                # ใช้ Theo Usage = values[8]
                # =================================================

                act_usage = values[6]

                theo_usage = values[8]

                # =================================================
                # Description
                # =================================================

                first_number = number_pattern.search(
                    block_text
                )

                if first_number:

                    description = (
                        block_text[
                            :first_number.start()
                        ].strip()
                    )

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
                # สูตร
                #
                # Theo Usage × 10,000 ÷ Net Sale
                #
                # ผลลัพธ์เป็น "ตัวเลข"
                # ไม่ใช่เปอร์เซ็นต์
                # =================================================

                theo_10000 = (
                    theo_usage * 10000
                ) / net_sale

                rows.append(
                    (
                        code,
                        description,
                        act_usage,
                        theo_usage,
                        theo_10000
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
        theo_usage = row[3]

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

        self.root.title(
            APP_TITLE
        )

        self.root.geometry(
            "1150x680"
        )

        self.root.minsize(
            900,
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
                "คำนวณ Theo Usage × 10,000 ÷ Net Sale "
                "โดยผลลัพธ์เป็นตัวเลข"
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
        # TABLE FRAME
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

        # =================================================
        # TABLE COLUMNS
        # =================================================

        columns = (
            "code",
            "desc",
            "act",
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
            "act",
            text="Act. Usage"
        )

        self.tree.heading(
            "theo",
            text="Theo. Usage"
        )

        self.tree.heading(
            "result",
            text="Theo × 10,000 ÷ Net Sale"
        )

        # =================================================
        # COLUMN WIDTH
        # =================================================

        self.tree.column(
            "code",
            width=120,
            anchor="w"
        )

        self.tree.column(
            "desc",
            width=430,
            anchor="w"
        )

        self.tree.column(
            "act",
            width=130,
            anchor="e"
        )

        self.tree.column(
            "theo",
            width=130,
            anchor="e"
        )

        self.tree.column(
            "result",
            width=220,
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

            # ล้างข้อมูลเดิม
            for item in self.tree.get_children():

                self.tree.delete(item)

            # แสดงข้อมูล
            for (
                code,
                description,
                act_usage,
                theo_usage,
                result
            ) in self.rows:

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        code,
                        description,
                        f"{act_usage:,.2f}",
                        f"{theo_usage:,.2f}",
                        f"{result:,.2f}"
                    )
                )

            # Info
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
                initialfile=(
                    "Theo_10000_Result.xlsx"
                )
            )

            if not path:
                return

            # =================================================
            # เตรียมข้อมูล
            # =================================================

            data = []

            for (
                code,
                description,
                act_usage,
                theo_usage,
                result
            ) in self.rows:

                data.append(
                    {
                        "Item Code": code,
                        "Description": description,
                        "Act. Usage": act_usage,
                        "Theo. Usage": theo_usage,
                        "Theo × 10,000 ÷ Net Sale": result
                    }
                )

            df = pd.DataFrame(data)

            # =================================================
            # Export
            # =================================================

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

        root.iconname(
            APP_TITLE
        )

    except Exception:

        pass

    app = App(root)

    root.mainloop()
