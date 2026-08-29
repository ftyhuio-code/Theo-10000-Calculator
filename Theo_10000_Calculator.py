import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pdfplumber


APP_TITLE = "Theo Usage Calculator"


def num(value):
    """Convert text number to float."""
    value = value.replace(",", "").strip()

    if value.startswith("(") and value.endswith(")"):
        return -float(value[1:-1])

    return float(value)


def extract_pdf(pdf_path):
    """Read PDF and extract Net Sale + Theo Usage."""
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += "\n" + page_text

    # -----------------------------
    # Find Net Sale
    # -----------------------------
    match = re.search(
        r"Net\s+Sale\s+([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if not match:
        raise ValueError("ไม่พบ Net Sale ใน PDF")

    net_sale = num(match.group(1))

    if net_sale == 0:
        raise ValueError("Net Sale เป็น 0 ไม่สามารถคำนวณได้")

    # -----------------------------
    # Split lines
    # -----------------------------
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    rows = []

    # Item code เช่น THK0002, THF2100
    code_pattern = re.compile(
        r"TH[A-Z0-9]+",
        re.IGNORECASE
    )

    # Number pattern
    number_pattern = re.compile(
        r"\(?-?\d[\d,]*(?:\.\d+)?\)?"
    )

    i = 0

    while i < len(lines):

        line = lines[i]

        # -----------------------------
        # Detect Item Code
        # -----------------------------
        code_match = code_pattern.fullmatch(
            line.replace(" ", "")
        )

        if not code_match:
            i += 1
            continue

        code = code_match.group(0).upper()

        # -----------------------------
        # Collect following lines
        # -----------------------------
        block = []

        j = i + 1

        while j < len(lines):

            next_line = lines[j]

            # Stop when another item starts
            if code_pattern.fullmatch(
                next_line.replace(" ", "")
            ):
                break

            # Stop at report sections
            if next_line.startswith(
                (
                    "Sub Total:",
                    "Item Group:",
                    "Total All Item Groups",
                    "QSA -",
                )
            ):
                break

            block.append(next_line)

            combined = " ".join(block)

            numbers = number_pattern.findall(combined)

            # Normal item row contains at least 8 numbers:
            #
            # Opening
            # Purchases
            # Return
            # Transfer In
            # Transfer Out
            # Closing
            # Act Usage
            # Theo Usage
            #
            if len(numbers) >= 8:
                break

            j += 1

        block_text = " ".join(block)

        numbers = number_pattern.findall(block_text)

        if len(numbers) >= 8:

            try:
                values = [
                    num(value)
                    for value in numbers
                ]

                # Theo Usage = numeric field #8
                theo_usage = values[7]

                # -----------------------------
                # Find description
                # -----------------------------
                first_number = number_pattern.search(
                    block_text
                )

                if first_number:
                    description = (
                        block_text[:first_number.start()]
                        .strip()
                    )
                else:
                    description = block_text.strip()

                # Clean description
                description = re.sub(
                    r"\s+",
                    " ",
                    description
                )

                if description:

                    # -----------------------------
                    # Theo Usage calculation
                    #
                    # Theo Usage × 10,000 ÷ Net Sale
                    #
                    # IMPORTANT:
                    # Result is a NUMBER, NOT %
                    # -----------------------------
                    theo_10000 = (
                        theo_usage * 10000 / net_sale
                    )

                    rows.append(
                        (
                            code,
                            description,
                            theo_usage,
                            theo_10000
                        )
                    )

            except (ValueError, IndexError):
                pass

        # Move to next section
        i = max(i + 1, j)

    # -----------------------------
    # Remove duplicates
    # -----------------------------
    clean_rows = []
    seen = set()

    for row in rows:

        code, description, theo, result = row

        key = (
            code,
            round(theo, 6)
        )

        if key in seen:
            continue

        seen.add(key)

        # Keep positive Theo values
        if theo >= 0:
            clean_rows.append(row)

    return net_sale, clean_rows


class App:

    def __init__(self, root):

        self.root = root

        self.root.title(APP_TITLE)
        self.root.geometry("1050x650")
        self.root.minsize(850, 550)

        self.rows = []
        self.net_sale = 0

        # -----------------------------
        # Top section
        # -----------------------------
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
            font=("Segoe UI", 18, "bold")
        ).pack(
            anchor="w"
        )

        ttk.Label(
            top,
            text=(
                "Theo Usage × 10,000 ÷ Net Sale "
                "และแสดงผลเป็นตัวเลข"
            )
        ).pack(
            anchor="w",
            pady=(4, 10)
        )

        # -----------------------------
        # Buttons
        # -----------------------------
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

        # -----------------------------
        # Table
        # -----------------------------
        frame = ttk.Frame(
            root,
            padding=(12, 0, 12, 12)
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

        # Headers
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
            text="Theo Usage × 10,000 ÷ Sales"
        )

        # Column sizes
        self.tree.column(
            "code",
            width=120
        )

        self.tree.column(
            "desc",
            width=450
        )

        self.tree.column(
            "theo",
            width=130,
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

        # -----------------------------
        # Scrollbar
        # -----------------------------
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

    # ==================================================
    # OPEN PDF
    # ==================================================

    def open_pdf(self):

        path = filedialog.askopenfilename(
            title="เลือก Inventory Activity Standard Report",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("All files", "*.*")
            ]
        )

        if not path:
            return

        try:

            self.net_sale, self.rows = extract_pdf(path)

            # Clear table
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Insert rows
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
                    f"Net Sale: {self.net_sale:,.2f} "
                    f"| พบ {len(self.rows)} รายการ"
                )
            )

        except Exception as error:

            messagebox.showerror(
                "อ่าน PDF ไม่สำเร็จ",
                str(error)
            )

    # ==================================================
    # EXPORT EXCEL
    # ==================================================

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
                    ("Excel Workbook", "*.xlsx")
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
                        "Theo Usage × 10,000 ÷ Net Sale": result
                    }
                )

            df = pd.DataFrame(data)

            df.to_excel(
                path,
                index=False
            )

            messagebox.showinfo(
                "สำเร็จ",
                f"บันทึกไฟล์แล้ว\n\n{path}"
            )

        except Exception as error:

            messagebox.showerror(
                "Export ไม่สำเร็จ",
                str(error)
            )


# ======================================================
# MAIN
# ======================================================

if __name__ == "__main__":

    root = tk.Tk()

    try:
        root.iconname(APP_TITLE)
    except Exception:
        pass

    app = App(root)

    root.mainloop()
