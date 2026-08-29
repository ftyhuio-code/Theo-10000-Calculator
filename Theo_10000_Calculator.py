import re
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

import pdfplumber


APP_TITLE = "Theo Usage Calculator"

SETTINGS_FILE = Path.home() / "Theo_Usage_Calculator_Settings.json"

DEFAULT_COLUMN = 8

COLUMN_NAMES = {
    1: "Opening",
    2: "Purchases",
    3: "Return",
    4: "Transfer In",
    5: "Transfer Out",
    6: "Closing",
    7: "Act. Usage",
    8: "Theo. Usage",
    9: "Variance",
    10: "Variance Amount",
}


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
# SETTINGS
# =========================================================

def load_settings():

    try:
        if SETTINGS_FILE.exists():

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

                if isinstance(data, dict):
                    return data

    except Exception:
        pass

    return {
        "default_column": DEFAULT_COLUMN,
        "items": {}
    }


def save_settings(settings):

    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            settings,
            file,
            ensure_ascii=False,
            indent=4
        )


# =========================================================
# COLUMN
# =========================================================

def get_column_number(value):

    try:

        number = int(value)

        if number < 1 or number > 10:
            return DEFAULT_COLUMN

        return number

    except Exception:

        return DEFAULT_COLUMN


# =========================================================
# PDF EXTRACTION
# =========================================================

def extract_pdf(pdf_path, default_column, item_settings):

    text_parts = []

    # -----------------------------------------------------
    # อ่าน PDF
    # -----------------------------------------------------

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text() or ""

            if page_text:
                text_parts.append(page_text)

    text = "\n".join(text_parts)

    # -----------------------------------------------------
    # Net Sale
    # -----------------------------------------------------

    net_sale_match = re.search(
        r"Net\s+Sale\s+([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if not net_sale_match:

        raise ValueError(
            "ไม่พบ Net Sale ใน PDF"
        )

    net_sale = num(
        net_sale_match.group(1)
    )

    if net_sale == 0:

        raise ValueError(
            "Net Sale เป็น 0 ไม่สามารถคำนวณได้"
        )

    # -----------------------------------------------------
    # Lines
    # -----------------------------------------------------

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

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

        block = []

        j = i + 1

        while j < len(lines):

            next_line = lines[j]

            if item_code_pattern.fullmatch(
                next_line.replace(" ", "")
            ):
                break

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

            # รายการมาตรฐานมีอย่างน้อย 10 คอลัมน์
            if len(numbers) >= 10:
                break

            j += 1

        block_text = " ".join(block)

        number_strings = number_pattern.findall(
            block_text
        )

        if len(number_strings) >= 8:

            try:

                values = [
                    num(value)
                    for value in number_strings
                ]

                # -------------------------------------------------
                # เลือกคอลัมน์
                #
                # ถ้ามีการตั้งเฉพาะ Item
                # ให้ใช้ค่าของ Item นั้น
                #
                # ถ้าไม่มี
                # ให้ใช้ค่า Default
                # -------------------------------------------------

                if code in item_settings:

                    column_number = get_column_number(
                        item_settings[code]
                    )

                else:

                    column_number = get_column_number(
                        default_column
                    )

                selected_value = 0.0

                index = column_number - 1

                if 0 <= index < len(values):

                    selected_value = values[index]

                # -------------------------------------------------
                # Description
                # -------------------------------------------------

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

                    i = max(
                        i + 1,
                        j
                    )

                    continue

                # -------------------------------------------------
                # สูตร
                # -------------------------------------------------

                result = (
                    selected_value * 10000
                ) / net_sale

                rows.append(
                    {
                        "code": code,
                        "description": description,
                        "theo_usage": selected_value,
                        "result": result,
                        "column": column_number,
                        "column_name": COLUMN_NAMES.get(
                            column_number,
                            f"Column {column_number}"
                        )
                    }
                )

            except Exception:

                pass

        i = max(
            i + 1,
            j
        )

    # =====================================================
    # Remove duplicates
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
            "1150x700"
        )

        self.root.minsize(
            900,
            550
        )

        self.rows = []

        self.net_sale = 0

        self.settings = load_settings()

        self.default_column = get_column_number(
            self.settings.get(
                "default_column",
                DEFAULT_COLUMN
            )
        )

        self.item_settings = self.settings.get(
            "items",
            {}
        )

        self.loading_window = None

        self.create_ui()

    # =====================================================
    # UI
    # =====================================================

    def create_ui(self):

        top = ttk.Frame(
            self.root,
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
                "คำนวณค่าจากคอลัมน์ที่เลือก × 10,000 ÷ Net Sale"
            )
        ).pack(
            anchor="w",
            pady=(4, 10)
        )

        bar = ttk.Frame(top)

        bar.pack(
            fill="x"
        )

        self.pdf_button = ttk.Button(
            bar,
            text="📄 เลือก PDF",
            command=self.open_pdf
        )

        self.pdf_button.pack(
            side="left"
        )

        self.settings_button = ttk.Button(
            bar,
            text="⚙ ตั้งค่า",
            command=self.open_settings
        )

        self.settings_button.pack(
            side="left",
            padx=8
        )

        self.export_button = ttk.Button(
            bar,
            text="📊 Export Excel",
            command=self.export_excel
        )

        self.export_button.pack(
            side="left"
        )

        self.info = ttk.Label(
            bar,
            text="ยังไม่ได้เลือกไฟล์"
        )

        self.info.pack(
            side="left",
            padx=10
        )

        # =================================================
        # TABLE
        # =================================================

        frame = ttk.Frame(
            self.root,
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
            "no",
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

        self.tree.heading(
            "no",
            text="ลำดับ"
        )

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

        self.tree.column(
            "no",
            width=60,
            anchor="center"
        )

        self.tree.column(
            "code",
            width=120
        )

        self.tree.column(
            "desc",
            width=520
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
    # LOADING
    # =====================================================

    def show_loading(self):

        if self.loading_window:
            return

        self.loading_window = tk.Toplevel(
            self.root
        )

        self.loading_window.title(
            "กำลังประมวลผล"
        )

        self.loading_window.geometry(
            "380x150"
        )

        self.loading_window.resizable(
            False,
            False
        )

        self.loading_window.transient(
            self.root
        )

        self.loading_window.grab_set()

        frame = ttk.Frame(
            self.loading_window,
            padding=20
        )

        frame.pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            frame,
            text="กำลังอ่านและประมวลผล PDF...",
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        ).pack(
            pady=(5, 12)
        )

        self.progress = ttk.Progressbar(
            frame,
            mode="indeterminate"
        )

        self.progress.pack(
            fill="x"
        )

        self.progress.start(
            10
        )

    def hide_loading(self):

        if self.loading_window:

            try:
                self.progress.stop()
            except Exception:
                pass

            try:
                self.loading_window.grab_release()
            except Exception:
                pass

            self.loading_window.destroy()

            self.loading_window = None

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

        self.show_loading()

        self.pdf_button.config(
            state="disabled"
        )

        self.settings_button.config(
            state="disabled"
        )

        self.export_button.config(
            state="disabled"
        )

        thread = threading.Thread(
            target=self.process_pdf_thread,
            args=(path,),
            daemon=True
        )

        thread.start()

    # =====================================================
    # PDF THREAD
    # =====================================================

    def process_pdf_thread(self, path):

        try:

            net_sale, rows = extract_pdf(
                path,
                self.default_column,
                self.item_settings
            )

            self.root.after(
                0,
                lambda: self.pdf_success(
                    net_sale,
                    rows
                )
            )

        except Exception as error:

            self.root.after(
                0,
                lambda: self.pdf_error(
                    str(error)
                )
            )

    # =====================================================
    # SUCCESS
    # =====================================================

    def pdf_success(
        self,
        net_sale,
        rows
    ):

        self.net_sale = net_sale

        self.rows = rows

        for item in self.tree.get_children():

            self.tree.delete(item)

        for index, row in enumerate(
            self.rows,
            start=1
        ):

            self.tree.insert(
                "",
                "end",
                values=(
                    index,
                    row["code"],
                    row["description"],
                    f'{row["theo_usage"]:,.2f}',
                    f'{row["result"]:,.2f}'
                )
            )

        self.info.config(
            text=(
                f"Net Sale: "
                f"{self.net_sale:,.2f}"
                f" | พบ "
                f"{len(self.rows)} รายการ"
            )
        )

        self.hide_loading()

        self.pdf_button.config(
            state="normal"
        )

        self.settings_button.config(
            state="normal"
        )

        self.export_button.config(
            state="normal"
        )

    # =====================================================
    # ERROR
    # =====================================================

    def pdf_error(self, error):

        self.hide_loading()

        self.pdf_button.config(
            state="normal"
        )

        self.settings_button.config(
            state="normal"
        )

        self.export_button.config(
            state="normal"
        )

        messagebox.showerror(
            "อ่าน PDF ไม่สำเร็จ",
            error
        )

    # =====================================================
    # SETTINGS
    # =====================================================

    def open_settings(self):

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "ตั้งค่าการคำนวณ"
        )

        window.geometry(
            "950x650"
        )

        window.minsize(
            800,
            500
        )

        # =================================================
        # TITLE
        # =================================================

        top = ttk.Frame(
            window,
            padding=12
        )

        top.pack(
            fill="x"
        )

        ttk.Label(
            top,
            text="⚙ ตั้งค่าการคำนวณ",
            font=(
                "Segoe UI",
                16,
                "bold"
            )
        ).pack(
            anchor="w"
        )

        ttk.Label(
            top,
            text=(
                "สามารถเปลี่ยนทั้งหมด หรือเปลี่ยนเฉพาะรายการได้"
            )
        ).pack(
            anchor="w",
            pady=(4, 10)
        )

        # =================================================
        # MODE 1 - CHANGE ALL
        # =================================================

        all_frame = ttk.LabelFrame(
            window,
            text="1. เปลี่ยนทั้งหมด",
            padding=12
        )

        all_frame.pack(
            fill="x",
            padx=12,
            pady=(0, 10)
        )

        ttk.Label(
            all_frame,
            text="คอลัมน์สำหรับทุกรายการ:"
        ).pack(
            side="left"
        )

        all_var = tk.StringVar()

        all_combo = ttk.Combobox(
            all_frame,
            textvariable=all_var,
            values=[
                f"{number} - {name}"
                for number, name
                in COLUMN_NAMES.items()
            ],
            state="readonly",
            width=30
        )

        all_combo.set(
            f"{self.default_column} - "
            f"{COLUMN_NAMES[self.default_column]}"
        )

        all_combo.pack(
            side="left",
            padx=8
        )

        def get_combo_number(combo):

            match = re.match(
                r"(\d+)",
                combo.get()
            )

            if not match:
                return DEFAULT_COLUMN

            return get_column_number(
                match.group(1)
            )

        def change_all():

            number = get_combo_number(
                all_combo
            )

            self.default_column = number

            # ---------------------------------------------
            # ล้าง override ราย Item
            # ---------------------------------------------

            self.item_settings.clear()

            self.settings[
                "default_column"
            ] = number

            self.settings[
                "items"
            ] = self.item_settings

            save_settings(
                self.settings
            )

            refresh_table()

            messagebox.showinfo(
                "สำเร็จ",
                (
                    "เปลี่ยนทุก Item เป็น\n\n"
                    f"{number} - "
                    f"{COLUMN_NAMES[number]}"
                ),
                parent=window
            )

        ttk.Button(
            all_frame,
            text="เปลี่ยนทั้งหมด",
            command=change_all
        ).pack(
            side="left",
            padx=8
        )

        # =================================================
        # MODE 2 - CHANGE SINGLE
        # =================================================

        single_frame = ttk.LabelFrame(
            window,
            text="2. เปลี่ยนรายรายการ",
            padding=12
        )

        single_frame.pack(
            fill="both",
            expand=True,
            padx=12
        )

        # -------------------------------------------------
        # Table
        # -------------------------------------------------

        table_frame = ttk.Frame(
            single_frame
        )

        table_frame.pack(
            fill="both",
            expand=True
        )

        columns = (
            "no",
            "code",
            "desc",
            "column"
        )

        settings_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        settings_tree.heading(
            "no",
            text="ลำดับ"
        )

        settings_tree.heading(
            "code",
            text="Item Code"
        )

        settings_tree.heading(
            "desc",
            text="Description"
        )

        settings_tree.heading(
            "column",
            text="คอลัมน์ที่ใช้"
        )

        settings_tree.column(
            "no",
            width=60,
            anchor="center"
        )

        settings_tree.column(
            "code",
            width=120
        )

        settings_tree.column(
            "desc",
            width=430
        )

        settings_tree.column(
            "column",
            width=180,
            anchor="center"
        )

        settings_tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        settings_scroll = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=settings_tree.yview
        )

        settings_scroll.pack(
            side="right",
            fill="y"
        )

        settings_tree.configure(
            yscrollcommand=settings_scroll.set
        )

        # -------------------------------------------------
        # Refresh Table
        # -------------------------------------------------

        def refresh_table():

            for item in settings_tree.get_children():

                settings_tree.delete(item)

            for index, row in enumerate(
                self.rows,
                start=1
            ):

                code = row["code"]

                if code in self.item_settings:

                    column = get_column_number(
                        self.item_settings[code]
                    )

                else:

                    column = self.default_column

                settings_tree.insert(
                    "",
                    "end",
                    iid=str(index),
                    values=(
                        index,
                        code,
                        row["description"],
                        (
                            f"{column} - "
                            f"{COLUMN_NAMES[column]}"
                        )
                    )
                )

        refresh_table()

        # =================================================
        # SINGLE EDIT
        # =================================================

        edit_frame = ttk.Frame(
            single_frame,
            padding=(0, 10, 0, 0)
        )

        edit_frame.pack(
            fill="x"
        )

        ttk.Label(
            edit_frame,
            text="คอลัมน์:"
        ).pack(
            side="left"
        )

        single_var = tk.StringVar()

        single_combo = ttk.Combobox(
            edit_frame,
            textvariable=single_var,
            values=[
                f"{number} - {name}"
                for number, name
                in COLUMN_NAMES.items()
            ],
            state="readonly",
            width=30
        )

        single_combo.set(
            f"{self.default_column} - "
            f"{COLUMN_NAMES[self.default_column]}"
        )

        single_combo.pack(
            side="left",
            padx=8
        )

        def load_selected(event=None):

            selected = settings_tree.selection()

            if not selected:
                return

            index = int(
                selected[0]
            )

            row = self.rows[
                index - 1
            ]

            code = row["code"]

            if code in self.item_settings:

                column = get_column_number(
                    self.item_settings[code]
                )

            else:

                column = self.default_column

            single_combo.set(
                f"{column} - "
                f"{COLUMN_NAMES[column]}"
            )

        settings_tree.bind(
            "<<TreeviewSelect>>",
            load_selected
        )

        def change_single():

            selected = settings_tree.selection()

            if not selected:

                messagebox.showwarning(
                    "ยังไม่ได้เลือก",
                    "กรุณาเลือกรายการก่อน",
                    parent=window
                )

                return

            index = int(
                selected[0]
            )

            row = self.rows[
                index - 1
            ]

            code = row["code"]

            column = get_combo_number(
                single_combo
            )

            # ---------------------------------------------
            # บันทึกเฉพาะ Item นี้
            # ---------------------------------------------

            self.item_settings[
                code
            ] = column

            self.settings[
                "default_column"
            ] = self.default_column

            self.settings[
                "items"
            ] = self.item_settings

            save_settings(
                self.settings
            )

            refresh_table()

            # เลือกรายการเดิม
            settings_tree.selection_set(
                str(index)
            )

            messagebox.showinfo(
                "สำเร็จ",
                (
                    f"{code}\n\n"
                    f"เปลี่ยนเป็น "
                    f"{column} - "
                    f"{COLUMN_NAMES[column]}"
                ),
                parent=window
            )

        ttk.Button(
            edit_frame,
            text="เปลี่ยนรายการที่เลือก",
            command=change_single
        ).pack(
            side="left",
            padx=8
        )

        # =================================================
        # BOTTOM
        # =================================================

        bottom = ttk.Frame(
            window,
            padding=12
        )

        bottom.pack(
            fill="x"
        )

        def reset_all():

            answer = messagebox.askyesno(
                "ยืนยัน",
                (
                    "ต้องการรีเซ็ตทั้งหมดกลับเป็น "
                    "คอลัมน์ 8 - Theo. Usage ใช่หรือไม่?"
                ),
                parent=window
            )

            if not answer:
                return

            self.default_column = DEFAULT_COLUMN

            self.item_settings.clear()

            self.settings[
                "default_column"
            ] = DEFAULT_COLUMN

            self.settings[
                "items"
            ] = {}

            save_settings(
                self.settings
            )

            all_combo.set(
                "8 - Theo. Usage"
            )

            single_combo.set(
                "8 - Theo. Usage"
            )

            refresh_table()

        ttk.Button(
            bottom,
            text="↩ รีเซ็ตทั้งหมดเป็น 8",
            command=reset_all
        ).pack(
            side="left"
        )

        ttk.Button(
            bottom,
            text="ปิด",
            command=window.destroy
        ).pack(
            side="right"
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

            for index, row in enumerate(
                self.rows,
                start=1
            ):

                data.append(
                    {
                        "ลำดับ": index,
                        "Item Code": row["code"],
                        "Description": row["description"],
                        "Theo Usage": row["theo_usage"],
                        "ผลลัพธ์": row["result"],
                        "คอลัมน์ที่ใช้": row["column"],
                        "ชื่อคอลัมน์": row["column_name"]
                    }
                )

            df = pd.DataFrame(
                data
            )

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

    app = App(
        root
    )

    root.mainloop()
