import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pdfplumber


APP_TITLE = "Theo Usage × 10,000 Calculator"


# =========================================================
# NUMBER
# =========================================================

NUMBER_RE = re.compile(
    r"\(?-?\d[\d,]*(?:\.\d+)?\)?"
)


def to_number(value):
    """แปลงข้อความตัวเลขจาก PDF เป็น float"""
    value = str(value).strip().replace(",", "")

    if not value:
        return 0.0

    negative = (
        value.startswith("(")
        and value.endswith(")")
    )

    value = value.strip("()")

    try:
        number = float(value)
    except ValueError:
        return 0.0

    return -number if negative else number


# =========================================================
# FIND NET SALE
# =========================================================

def find_net_sale(text):

    patterns = [
        r"Net\s+Sale\s*[:=]?\s*([\d,]+(?:\.\d+)?)",
        r"Net\s+Sales\s*[:=]?\s*([\d,]+(?:\.\d+)?)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = to_number(
                match.group(1)
            )

            if value > 0:
                return value

    raise ValueError(
        "ไม่พบ Net Sale ใน PDF"
    )


# =========================================================
# CHECK ITEM CODE
# =========================================================

ITEM_CODE_RE = re.compile(
    r"^TH[A-Z0-9]+$",
    re.IGNORECASE
)


def is_item_code(line):

    return bool(
        ITEM_CODE_RE.fullmatch(
            line.replace(" ", "")
        )
    )


# =========================================================
# EXTRACT DESCRIPTION
# =========================================================

def extract_description(text):

    match = NUMBER_RE.search(text)

    if not match:
        return text.strip()

    description = text[
        :match.start()
    ].strip()

    description = re.sub(
        r"\s+",
        " ",
        description
    )

    return description


# =========================================================
# EXTRACT PDF
# =========================================================

def extract_pdf(pdf_path):

    # -----------------------------------------------------
    # อ่าน PDF
    # -----------------------------------------------------

    pages_text = []

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = (
                page.extract_text(
                    x_tolerance=2,
                    y_tolerance=3
                )
                or ""
            )

            if page_text:
                pages_text.append(
                    page_text
                )

    if not pages_text:

        raise ValueError(
            "ไม่สามารถอ่านข้อความจาก PDF ได้"
        )

    text = "\n".join(
        pages_text
    )

    # -----------------------------------------------------
    # Net Sale
    # -----------------------------------------------------

    net_sale = find_net_sale(
        text
    )

    # -----------------------------------------------------
    # Lines
    # -----------------------------------------------------

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    rows = []

    i = 0

    # =====================================================
    # อ่านข้อมูลแต่ละ Item
    # =====================================================

    while i < len(lines):

        line = lines[i]

        # -----------------------------------------------
        # หา Item Code
        # -----------------------------------------------

        if not is_item_code(line):

            i += 1
            continue

        code = (
            line
            .replace(" ", "")
            .upper()
        )

        # -----------------------------------------------
        # เก็บข้อความของ Item
        # -----------------------------------------------

        block = []

        j = i + 1

        while j < len(lines):

            next_line = lines[j]

            # Item ถัดไป
            if is_item_code(next_line):
                break

            # ส่วนสรุป
            if next_line.startswith(
                (
                    "Sub Total:",
                    "Item Group:",
                    "Total All Item Groups",
                    "QSA -",
                    "Grand Total"
                )
            ):
                break

            # Header ของตาราง ไม่เอา
            if (
                "Act. Usage" in next_line
                or "Theo. Usage" in next_line
                or "Variance" == next_line
            ):
                j += 1
                continue

            block.append(
                next_line
            )

            combined = " ".join(
                block
            )

            # -------------------------------------------------
            # รายการสินค้าจะมีข้อมูลตัวเลขหลายช่อง
            #
            # ต้องมีอย่างน้อย 9 ตัว
            # เพื่ออ่าน Theo Usage
            # -------------------------------------------------

            number_count = len(
                NUMBER_RE.findall(
                    combined
                )
            )

            if number_count >= 9:
                break

            j += 1

        block_text = " ".join(
            block
        )

        # =================================================
        # อ่านตัวเลข
        # =================================================

        number_strings = NUMBER_RE.findall(
            block_text
        )

        if len(number_strings) < 9:

            i = max(
                i + 1,
                j
            )

            continue

        try:

            values = [
                to_number(x)
                for x in number_strings
            ]

            # =================================================
            # Inventory Activity Standard Report
            #
            # 0 = Opening
            # 1 = Purchases
            # 2 = Return
            # 3 = Transfer In
            # 4 = Transfer Out
            # 5 = Closing
            # 6 = Act. Usage
            # 7 = ค่าในคอลัมน์ระหว่างกลาง
            # 8 = Theo. Usage
            #
            # ใช้ Theo Usage เท่านั้น
            # =================================================

            theo_usage = values[8]

            # -------------------------------------------------
            # Description
            # -------------------------------------------------

            description = extract_description(
                block_text
            )

            if not description:

                i = max(
                    i + 1,
                    j
                )

                continue

            # -------------------------------------------------
            # คำนวณ
            # -------------------------------------------------

            result = (
                theo_usage
                * 10000
                / net_sale
            )

            # -------------------------------------------------
            # เก็บเฉพาะข้อมูลที่ต้องใช้
            # -------------------------------------------------

            rows.append(
                {
                    "code": code,
                    "description": description,
                    "theo_usage": theo_usage,
                    "result": result
                }
            )

        except (
            ValueError,
            IndexError,
            ZeroDivisionError
        ):

            pass

        i = max(
            i + 1,
            j
        )

    # =====================================================
    # ลบข้อมูลซ้ำ
    # =====================================================

    clean_rows = []

    seen = set()

    for row in rows:

        key = (
            row["code"],
            round(
                row["theo_usage"],
                6
            )
        )

        if key in seen:
            continue

        seen.add(key)

        clean_rows.append(
            row
        )

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
            "1050x650"
        )

        self.root.minsize(
            850,
            500
        )

        self.net_sale = 0.0
        self.rows = []

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
        # BUTTONS
        # =================================================

        bar = ttk.Frame(
            top
        )

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
            "description",
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
            "description",
            text="Description"
        )

        self.tree.heading(
            "theo",
            text="Theo Usage"
        )

        self.tree.heading(
            "result",
            text="Theo × 10,000 ÷ Net Sale"
        )

        # =================================================
        # WIDTH
        # =================================================

        self.tree.column(
            "code",
            width=130,
            anchor="w"
        )

        self.tree.column(
            "description",
            width=480,
            anchor="w"
        )

        self.tree.column(
            "theo",
            width=160,
            anchor="e"
        )

        self.tree.column(
            "result",
            width=230,
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

                self.tree.delete(
                    item
                )

            # แสดงข้อมูล
            for row in self.rows:

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        row["code"],
                        row["description"],
                        f"{row['theo_usage']:,.2f}",
                        f"{row['result']:,.4f}"
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

            # -------------------------------------------------
            # ถ้าอ่านได้แต่ไม่มีรายการ
            # -------------------------------------------------

            if not self.rows:

                messagebox.showwarning(
                    "ไม่พบข้อมูล",
                    (
                        "พบ Net Sale แล้ว แต่ไม่พบข้อมูล "
                        "Theo Usage\n\n"
                        "ตรวจสอบรูปแบบ PDF อีกครั้ง"
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

            data = []

            for row in self.rows:

                data.append(
                    {
                        "Item Code":
                            row["code"],

                        "Description":
                            row["description"],

                        "Theo Usage":
                            row["theo_usage"],

                        "Theo × 10,000 ÷ Net Sale":
                            row["result"]
                    }
                )

            df = pd.DataFrame(
                data
            )

            # ---------------------------------------------
            # เพิ่มข้อมูล Net Sale
            # ---------------------------------------------

            with pd.ExcelWriter(
                path,
                engine="openpyxl"
            ) as writer:

                df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Theo Result"
                )

                worksheet = writer.sheets[
                    "Theo Result"
                ]

                # ปรับความกว้างคอลัมน์
                worksheet.column_dimensions[
                    "A"
                ].width = 18

                worksheet.column_dimensions[
                    "B"
                ].width = 50

                worksheet.column_dimensions[
                    "C"
                ].width = 18

                worksheet.column_dimensions[
                    "D"
                ].width = 28

                # เพิ่ม Net Sale
                worksheet["F1"] = "Net Sale"
                worksheet["G1"] = self.net_sale

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

    App(root)

    root.mainloop()
