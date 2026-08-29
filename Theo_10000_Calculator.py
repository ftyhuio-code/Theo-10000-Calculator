import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pdfplumber

APP_TITLE = "Theo × 10,000 Calculator"


def num(s):
    s = s.replace(",", "").strip()
    if s.startswith("(") and s.endswith(")"):
        return -float(s[1:-1])
    return float(s)


def extract_pdf(pdf_path):
    """
    อ่าน Inventory Activity Standard Report

    สูตร:
        Theo Usage × 10,000 ÷ Net Sale

    สำคัญ:
    พยายามอ่านค่าจากตำแหน่ง Theo. Usage
    โดยอาศัยหัวตารางและโครงสร้างแถว
    """

    all_lines = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_lines.extend(
                line.strip()
                for line in text.splitlines()
                if line.strip()
            )

    text_all = "\n".join(all_lines)

    # ---------------------------------------------------------
    # หา Net Sale
    # ---------------------------------------------------------
    net_sale = None

    patterns = [
        r"Net Sale\s+([\d,]+\.\d+)",
        r"Net\s+Sale\s+([\d,]+\.\d+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text_all, re.I)
        if m:
            net_sale = num(m.group(1))
            break

    if net_sale is None:
        raise ValueError("ไม่พบ Net Sale ใน PDF")

    # ---------------------------------------------------------
    # หา Item rows
    # ---------------------------------------------------------
    rows = []

    # Item code ของรายงาน เช่น THK0002 / THF2100
    item_code_pattern = re.compile(
        r"^TH[A-Z0-9]{3,}$",
        re.I
    )

    # ตัวเลข
    number_pattern = re.compile(
        r"?-?\d[\d,]*(?:\.\d+)??"
    )

    i = 0

    while i < len(all_lines):

        line = all_lines[i]
        code = line.replace(" ", "")

        if not item_code_pattern.fullmatch(code):
            i += 1
            continue

        # -----------------------------------------------------
        # เจอ Item Code
        # -----------------------------------------------------
        item_code = code.upper()

        block = []
        j = i + 1

        while j < len(all_lines):

            current = all_lines[j]

            # เจอ Item Code ใหม่ = จบแถวเดิม
            if item_code_pattern.fullmatch(
                current.replace(" ", "")
            ):
                break

            # เจอส่วนสรุป = จบ
            stop_words = (
                "Sub Total:",
                "Item Group:",
                "Total All Item Groups",
                "QSA -",
            )

            if current.startswith(stop_words):
                break

            block.append(current)

            # ป้องกันอ่านยาวเกินไป
            if len(block) >= 5:
                break

            j += 1

        block_text = " ".join(block)

        # -----------------------------------------------------
        # ดึงตัวเลขทั้งหมด
        # -----------------------------------------------------
        matches = number_pattern.findall(block_text)

        if len(matches) >= 8:

            try:
                values = [num(x) for x in matches]

                # -------------------------------------------------
                # โครงสร้างมาตรฐาน:
                #
                # 1 Opening
                # 2 Purchases
                # 3 Return
                # 4 Transfer In
                # 5 Transfer Out
                # 6 Closing
                # 7 Act. Usage
                # 8 Theo. Usage
                # 9 Variance
                # 10 Variance Amount
                # ...
                #
                # Theo Usage = index 7
                # -------------------------------------------------

                theo_usage = values[7]

                # หา Description
                desc_match = re.match(
                    r"^(.*?)(?=?-?\d[\d,]*(?:\.\d+)??)",
                    block_text
                )

                if desc_match:
                    description = desc_match.group(1).strip()
                else:
                    description = block_text

                # ตัดหน่วยที่อาจติดด้านหน้า
                description = re.sub(
                    r"^(PC|PA|CU|EA|KG|X)\s+",
                    "",
                    description,
                    flags=re.I
                ).strip()

                result = (
                    theo_usage * 10000 / net_sale
                    if net_sale
                    else 0
                )

                rows.append(
                    (
                        item_code,
                        description,
                        theo_usage,
                        result
                    )
                )

            except (ValueError, IndexError):
                pass

        i = max(i + 1, j)

    # ---------------------------------------------------------
    # ลบรายการซ้ำ
    # ---------------------------------------------------------
    clean = []
    seen = set()

    for row in rows:

        key = (
            row[0],
            row[2]
        )

        if key in seen:
            continue

        seen.add(key)

        # ไม่เอา Theo ติดลบ
        if row[2] >= 0:
                   code_match = re.fullmatch(r"(TH[A-Z0-9]+)", line.replace(" ", ""))
        if code_match:
            code = code_match.group(1)
            j = i + 1
            block = []
            while j < len(lines) and not re.fullmatch(r"TH[A-Z0-9]+", lines[j].replace(" ", "")) \
                    and not lines[j].startswith(("Sub Total:", "Item Group:", "Total All Item Groups", "QSA -")):
                block.append(lines[j])
                # A data row normally contains many numeric values.
                if len(re.findall(r"(?<![A-Za-z])[-()]?\d[\d,]*\.?\d*(?:\)|\b)", " ".join(block))) >= 12:
                    break
                j += 1

            block_text = " ".join(block)
            # Extract numbers from the end of the row. Theo is the 8th numeric field:
            # Opening, Purchases, Return, Transfer In, Transfer Out, Closing, Act Usage, Theo Usage
            nums = re.findall(r"\(?-?\d[\d,]*\.?\d*\)?", block_text)
            if len(nums) >= 8:
                try:
                    values = [num(x) for x in nums]
                    theo = values[7]
                    # Description is the text before the first numeric value.
                    desc = re.split(r"\(?-?\d[\d,]*\.?\d*\)?", block_text, maxsplit=1)[0].strip()
                    if desc and not desc.startswith(("x ", "PC ", "PA ", "CU ")):
                        rows.append((code, desc, theo, theo * 10000 / net_sale if net_sale else 0))
                except Exception:
                    pass
            i = max(i + 1, j)
        else:
            i += 1

    # The text extraction above can be affected by wrapped rows.
    # Remove obvious subtotal/header duplicates.
    clean = []
    seen = set()
    for r in rows:
        key = (r[0], round(r[2], 6))
        if key not in seen and r[2] >= 0:
            seen.add(key)
            clean.append(r)

    return net_sale, clean

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1000x650")
        self.root.minsize(850, 550)
        self.rows = []
        self.net_sale = 0

        top = ttk.Frame(root, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text=APP_TITLE, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(top, text="เลือก Inventory Activity Standard Report PDF แล้วโปรแกรมจะคำนวณ Theo × 10,000 ÷ Net Sale").pack(anchor="w", pady=(4,10))

        bar = ttk.Frame(top)
        bar.pack(fill="x")
        ttk.Button(bar, text="📄 เลือก PDF", command=self.open_pdf).pack(side="left")
        ttk.Button(bar, text="📊 Export Excel", command=self.export_excel).pack(side="left", padx=8)
        self.info = ttk.Label(bar, text="ยังไม่ได้เลือกไฟล์")
        self.info.pack(side="left", padx=8)

        frame = ttk.Frame(root, padding=(12,0,12,12))
        frame.pack(fill="both", expand=True)

        cols = ("code","desc","theo","pct")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        self.tree.heading("code", text="Item Code")
        self.tree.heading("desc", text="Description")
        self.tree.heading("theo", text="Theo Usage")
        self.tree.heading("pct", text="% / 10,000 Sales")
        self.tree.column("code", width=120)
        self.tree.column("desc", width=520)
        self.tree.column("theo", width=120, anchor="e")
        self.tree.column("pct", width=160, anchor="e")
        self.tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files","*.pdf")])
        if not path:
            return
        try:
            self.net_sale, self.rows = extract_pdf(path)
            for item in self.tree.get_children():
                self.tree.delete(item)
            for code, desc, theo, pct in self.rows:
                self.tree.insert("", "end", values=(code, desc, f"{theo:,.2f}", f"{pct:,.2f}%"))
            self.info.config(text=f"Net Sale: {self.net_sale:,.2f} | พบ {len(self.rows)} รายการ")
        except Exception as e:
            messagebox.showerror("อ่าน PDF ไม่สำเร็จ", str(e))

    def export_excel(self):
        if not self.rows:
            messagebox.showwarning("ยังไม่มีข้อมูล", "กรุณาเลือก PDF ก่อน")
            return
        try:
            import pandas as pd
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Workbook","*.xlsx")],
                initialfile="Theo_10000_Result.xlsx"
            )
            if not path:
                return
            df = pd.DataFrame(self.rows, columns=["Item Code","Description","Theo Usage","% / 10,000 Sales"])
            df.to_excel(path, index=False)
            messagebox.showinfo("สำเร็จ", f"บันทึกไฟล์แล้ว\n{path}")
        except Exception as e:
            messagebox.showerror("Export ไม่สำเร็จ", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconname(APP_TITLE)
    except Exception:
        pass
    App(root)
    root.mainloop()
