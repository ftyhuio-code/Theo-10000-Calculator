import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import pdfplumber

APP_TITLE = "Theo × 10,000 Calculator"

def num(s):
    s = s.replace(",", "").strip()
    if s.startswith("(") and s.endswith(")"):
        return -float(s[1:-1])
    return float(s)

def extract_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += "\n" + (page.extract_text() or "")

    # Net Sale from the Summary page
    m = re.search(r"Net Sale\s+([\d,]+\.\d+)", text, re.I)
    if not m:
        raise ValueError("ไม่พบ Net Sale ใน PDF")
    net_sale = num(m.group(1))

    # Rows in this report end with:
    # ... Act. Usage, Theo. Usage, Variance, Variance Amount, Raw Waste, Finished Waste, Eff %, Stock Outstanding
    # We read the last numeric block on each item row.
    rows = []
    lines = [x.strip() for x in text.splitlines() if x.strip()]

    # Join wrapped descriptions by detecting an item code such as THK0002 / THF2100
    i = 0
    while i < len(lines):
        line = lines[i]
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
