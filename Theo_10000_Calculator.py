import re
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

import pdfplumber


APP_TITLE = "Theo Usage Calculator"

# =========================================================
# คอลัมน์จริงตามรายงาน "Inventory Activity Standard Report"
# (ตรวจสอบและยืนยันด้วยการรันจริงกับ PDF ตัวอย่างของผู้ใช้ ทุกค่าถูกต้อง
#  ตรงกับ "Sub Total" ที่พิมพ์อยู่ในรายงานเอง)
# =========================================================
#  1 Opening
#  2 Purchases
#  3 Return
#  4 Transfer In
#  5 Transfer Out
#  6 Closing
#  7 Act. Usage
#  8 Theo. Usage      <-- ค่าเริ่มต้น (แก้จาก 9 เป็น 8 เพราะรายงานจริงมี 14 คอลัมน์ ไม่ใช่ 10)
#  9 Variance
# 10 Variance Amount (฿)
# 11 Raw Waste
# 12 Finished Waste
# 13 Eff %
# 14 Stock Outstanding
# =========================================================

NUM_COLS = 14
DEFAULT_COLUMN = 8

SETTINGS_FILE = Path.home() / "Theo_Usage_Calculator_Settings.json"

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
    11: "Raw Waste",
    12: "Finished Waste",
    13: "Eff %",
    14: "Stock Outstanding",
}


# =========================================================
# NUMBER
# =========================================================

def num(value):

    value = str(value).replace(",", "").strip()

    if not value:
        return 0.0

    negative = value.startswith("(") or value.endswith(")")

    value = value.strip("()")

    if not value:
        return 0.0

    result = float(value)

    return -result if negative else result


# =========================================================
# SETTINGS
# =========================================================

def load_settings():

    default_data = {
        "default_column": DEFAULT_COLUMN,
        "items": {}
    }

    try:

        if not SETTINGS_FILE.exists():
            return default_data

        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return default_data

        default_column = data.get("default_column", DEFAULT_COLUMN)

        try:
            default_column = int(default_column)
        except Exception:
            default_column = DEFAULT_COLUMN

        if not 1 <= default_column <= NUM_COLS:
            default_column = DEFAULT_COLUMN

        items = data.get("items", {})

        if not isinstance(items, dict):
            items = {}

        return {
            "default_column": default_column,
            "items": items
        }

    except Exception:
        return default_data


def save_settings(settings):

    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(settings, file, ensure_ascii=False, indent=4)
    except Exception:
        pass


# =========================================================
# COLUMN HELPERS
# =========================================================

def column_text(number):
    number = int(number)
    name = COLUMN_NAMES.get(number, f"Column {number}")
    return f"{number} - {name}"


def get_column_from_combo(value):
    match = re.match(r"^\s*(\d+)", str(value))
    if not match:
        return DEFAULT_COLUMN
    number = int(match.group(1))
    if number < 1 or number > NUM_COLS:
        return DEFAULT_COLUMN
    return number


# =========================================================
# PDF EXTRACTION
#
# หมายเหตุสำคัญ (อ่านก่อนแก้โค้ดตรงนี้ในอนาคต):
#
# รายงานนี้มีโครงสร้างที่ทำให้ regex ตัดบรรทัดตรง ๆ ไม่พอ เพราะ:
#   1) รหัสสินค้า (Item Code) มักถูกตัดขึ้นบรรทัดใหม่กลางรหัส
#      เช่น "THK0002" กลายเป็น "THK000" อีกบรรทัดหนึ่ง แล้ว "2"
#      โผล่อีกบรรทัดหนึ่ง (มักอยู่ "หลัง" บรรทัดข้อมูลตัวเลข ไม่ใช่ก่อน)
#   2) ชื่อสินค้ามักมีตัวเลขปนอยู่ (เช่น "85-95GM 6PA", "24x330ml")
#      ถ้าใช้ regex ตัวเลขแบบเดิม (เก็บตัวเลข 8 ตัวแรกที่เจอ) ตัวเลข
#      พวกนี้จะปนเข้าไปเป็นค่าคอลัมน์ ทำให้ค่าทุกคอลัมน์เลื่อนผิด
#   3) แต่ละแถวสินค้ามีตัวเลขข้อมูลจริงคงที่ 14 ค่าเสมอ และตัวเลข
#      14 ค่านี้จะอยู่ "รวมกันเป็นกลุ่มเดียว" ในบรรทัดเดียว (บรรทัดที่มี
#      จำนวนตัวเลขมากที่สุดในบล็อกของแถวนั้น) แม้จะมีตัวเลขปนจาก
#      ชื่อ/หน่วยสินค้าอยู่ก่อนหน้าก็ตาม
#
# วิธีแก้: แบ่งข้อความเป็น "บล็อก" ต่อ 1 รายการ (ตั้งแต่พบรหัสสินค้า
# จนถึงก่อนรหัสสินค้าถัดไป/Sub Total/Item Group) แล้วในบล็อกนั้น
# เลือก "บรรทัดที่มีตัวเลขมากที่สุด" มาเป็นบรรทัดข้อมูลจริง แล้วหยิบ
# ตัวเลข 14 ตัว "ท้ายสุด" ของบรรทัดนั้นมาเป็นค่าคอลัมน์ 1-14
# (ยืนยันความถูกต้องแล้วโดยรวมค่าทุกรายการเทียบกับ "Sub Total"
#  ที่พิมพ์อยู่ในรายงานจริงเอง - ตรงกันทุกกลุ่มสินค้า)
# =========================================================

_NUMBER_PATTERN = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")
_ITEM_START_PATTERN = re.compile(r"^(TH[A-Z0-9]{3,})", re.IGNORECASE)
_OPEN_UNMATCHED_PAREN = re.compile(r"\(-?\d[\d,]*\.?\d*$")

_NOISE_PREFIXES = (
    "QSA - Strictly Confidential",
    "Inventory Activity Standard Report",
    "Date:",
    "Entity:",
)

# เส้นหัวตาราง/หัวกระดาษที่รายงานนี้พิมพ์ซ้ำทุกหน้า (ตรวจสอบจาก PDF จริง)
# ถ้ารายงานของคุณมีข้อความหัวกระดาษต่างจากนี้ ให้ปรับ set นี้ตามจริง
_NOISE_EXACT_LINES = {
    "QSA", "Stock", "ing", "Reporting", "Unit",
    "+ Transfer - Transfer Theo. Variance Finished",
    "Number Description Unit Opening + Purchases - Return Closing Act. Usage Variance Raw Waste Eff % Outstand",
    "In Out Usage Amount (\u0e3f) Waste",
}


def _clean_lines(text):

    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]

    lines = [
        line for line in raw_lines
        if line not in _NOISE_EXACT_LINES
        and not any(line.startswith(p) for p in _NOISE_PREFIXES)
    ]

    # ซ่อมกรณีวงเล็บปิด ")" ของตัวเลขติดลบถูกตัดไปขึ้นบรรทัดใหม่
    # (พบได้เมื่อค่าติดลบมีความยาวมาก เช่น เปอร์เซ็นต์ประสิทธิภาพติดลบสูง ๆ)
    for idx in range(len(lines)):
        if _OPEN_UNMATCHED_PAREN.search(lines[idx]):
            for k in range(idx + 1, min(idx + 4, len(lines))):
                if ")" in lines[k]:
                    lines[idx] = lines[idx] + ")"
                    lines[k] = re.sub(r"\)", "", lines[k]).strip()
                    break

    return lines


def _parse_rows(lines, progress_callback=None):

    n = len(lines)
    rows = []
    warnings = []
    current_group = None
    i = 0

    while i < n:

        if progress_callback and i % 25 == 0:
            percent = 70 + (i / max(n, 1)) * 20
            progress_callback(percent, "กำลังวิเคราะห์รายการสินค้า...")

        line = lines[i]

        if line.startswith("Item Group:"):
            current_group = line.split("Item Group:", 1)[1].strip()
            i += 1
            continue

        if line.startswith("Sub Total:") or line.startswith("Total All Item Groups"):
            i += 1
            continue

        match = _ITEM_START_PATTERN.match(line)

        if not match:
            i += 1
            continue

        prefix_code = match.group(1).upper()
        rest_first = line[match.end():].strip()

        # -----------------------------------------------
        # รวบรวมทุกบรรทัดของ "บล็อก" รายการนี้ จนกว่าจะเจอ
        # รายการถัดไป หรือ Sub Total / Item Group
        # -----------------------------------------------
        segment_texts = [rest_first] if rest_first else []
        j = i + 1

        while j < n:
            nxt = lines[j]
            if _ITEM_START_PATTERN.match(nxt):
                break
            if nxt.startswith("Sub Total:") or nxt.startswith("Item Group:") or nxt.startswith("Total All Item Groups"):
                break
            segment_texts.append(nxt)
            j += 1

        seg_matches = [
            (seg, list(_NUMBER_PATTERN.finditer(seg)))
            for seg in segment_texts
        ]

        if not seg_matches:
            # ไม่มีข้อความใด ๆ ตามหลังรหัสสินค้าเลย - ข้ามแบบไม่เก็บ (แทบไม่เกิดขึ้นจริง)
            i = j
            continue

        # บรรทัดที่มีจำนวนตัวเลขมากที่สุด = บรรทัดข้อมูลจริงของแถวนี้
        core_idx = max(range(len(seg_matches)), key=lambda k: len(seg_matches[k][1]))
        core_seg, core_matches = seg_matches[core_idx]

        needs_review = False

        if len(core_matches) >= NUM_COLS:
            last_n = core_matches[-NUM_COLS:]
            values = [num(m.group(0)) for m in last_n]
            core_desc = core_seg[:last_n[0].start()].strip()
        elif len(core_matches) > 0:
            # เจอตัวเลขไม่ครบ 14 ตัว - เก็บเท่าที่มี (เติม 0 ด้านหน้า) และตั้งค่าสถานะ
            # "ต้องตรวจสอบ" แทนที่จะทิ้งรายการไปเฉย ๆ แบบเวอร์ชันเก่า
            values = [0.0] * (NUM_COLS - len(core_matches)) + [num(m.group(0)) for m in core_matches]
            core_desc = core_seg[:core_matches[0].start()].strip()
            needs_review = True
        else:
            values = [0.0] * NUM_COLS
            core_desc = core_seg.strip()
            needs_review = True

        leading_segs = [seg for k, seg in enumerate(segment_texts) if k < core_idx]
        trailing_segs = [seg for k, seg in enumerate(segment_texts) if k > core_idx]
        trailing_text = " ".join(s for s in trailing_segs if s).strip()

        code = prefix_code

        suffix_match = re.match(r"^(\d{1,3})\b", trailing_text)

        if suffix_match:
            code = prefix_code + suffix_match.group(1)
            trailing_text = trailing_text[suffix_match.end():].strip()

        description = " ".join(t for t in leading_segs + [core_desc, trailing_text] if t)
        description = re.sub(r"\s+", " ", description).strip(" -")

        # รูปแบบข้อความผิดปกติ (วงเล็บไม่ครบคู่) มักแปลว่าค่าตัวเลขบางตัว
        # ของแถวนี้ถูกตัดขึ้นบรรทัดในตำแหน่งที่คาดเดายาก ควรเตือนให้ตรวจสอบเอง
        if description.count("(") != description.count(")"):
            needs_review = True

        rows.append({
            "code": code,
            "description": description,
            "group": current_group,
            "values": values,
            "needs_review": needs_review,
            "row_id": len(rows),
        })

        if needs_review:
            warnings.append(f"{code} - {description}")

        i = j

    return rows, warnings


def extract_pdf(pdf_path, progress_callback=None):

    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:

        total_pages = len(pdf.pages)

        if total_pages == 0:
            raise ValueError("PDF ไม่มีหน้า")

        for page_number, page in enumerate(pdf.pages, start=1):

            page_text = page.extract_text() or ""

            if page_text:
                text_parts.append(page_text)

            if progress_callback:
                percent = page_number / total_pages * 60
                progress_callback(percent, f"กำลังอ่าน PDF หน้า {page_number}/{total_pages}")

    text = "\n".join(text_parts)

    if progress_callback:
        progress_callback(65, "กำลังเตรียมข้อมูล...")

    # รองรับทั้ง "Net Sale 123.45" และ "Net Sale: 123.45"
    net_sale_match = re.search(r"Net\s+Sale\s*:?\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)

    if not net_sale_match:
        raise ValueError("ไม่พบ Net Sale ใน PDF")

    net_sale = num(net_sale_match.group(1))

    if net_sale == 0:
        raise ValueError("Net Sale เป็น 0 ไม่สามารถคำนวณได้")

    lines = _clean_lines(text)

    rows, warnings = _parse_rows(lines, progress_callback)

    # ลบรายการที่ซ้ำกันแบบทุกค่าเป๊ะ ๆ (ป้องกันข้อมูลซ้ำจากการอ่านผิดพลาด)
    clean_rows = []
    seen = set()

    for row in rows:
        key = (row["code"], row["description"], tuple(round(v, 6) for v in row["values"]))
        if key in seen:
            continue
        seen.add(key)
        row["row_id"] = len(clean_rows)
        clean_rows.append(row)

    if progress_callback:
        progress_callback(100, "ประมวลผลเสร็จแล้ว")

    return net_sale, clean_rows, warnings


# =========================================================
# APPLICATION
# =========================================================

class App:

    def __init__(self, root):

        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1200x700")
        self.root.minsize(950, 550)

        self.rows = []
        self.net_sale = 0

        self.settings = load_settings()
        self.default_column = int(self.settings.get("default_column", DEFAULT_COLUMN))
        self.item_settings = self.settings.get("items", {})

        self.loading_window = None
        self.progress_bar = None
        self.progress_label = None
        self.progress_percent = None
        self.loading_status = None

        self.create_ui()

    # =====================================================
    # UI
    # =====================================================

    def create_ui(self):

        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text=APP_TITLE, font=("Segoe UI", 18, "bold")).pack(anchor="w")

        ttk.Label(
            top,
            text="คำนวณค่าจากคอลัมน์ที่เลือก × 10,000 ÷ Net Sale"
        ).pack(anchor="w", pady=(4, 10))

        bar = ttk.Frame(top)
        bar.pack(fill="x")

        self.pdf_button = ttk.Button(bar, text="📄 เลือก PDF", command=self.open_pdf)
        self.pdf_button.pack(side="left")

        self.settings_button = ttk.Button(bar, text="⚙ ตั้งค่า", command=self.open_settings)
        self.settings_button.pack(side="left", padx=8)

        self.export_button = ttk.Button(bar, text="📊 Export Excel", command=self.export_excel)
        self.export_button.pack(side="left")

        self.export_button.config(state="disabled")

        self.info = ttk.Label(bar, text=f"ค่าเริ่มต้น: {column_text(self.default_column)}")
        self.info.pack(side="left", padx=12)

        frame = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        frame.pack(fill="both", expand=True)

        columns = ("no", "code", "desc", "theo", "result", "flag")

        self.tree = ttk.Treeview(frame, columns=columns, show="headings")

        self.tree.heading("no", text="ลำดับ")
        self.tree.heading("code", text="Item Code")
        self.tree.heading("desc", text="Description")
        self.tree.heading("theo", text="Theo Usage")
        self.tree.heading("result", text="ผลลัพธ์")
        self.tree.heading("flag", text="สถานะ")

        self.tree.column("no", width=55, anchor="center")
        self.tree.column("code", width=110, anchor="w")
        self.tree.column("desc", width=440, anchor="w")
        self.tree.column("theo", width=130, anchor="e")
        self.tree.column("result", width=150, anchor="e")
        self.tree.column("flag", width=110, anchor="center")

        self.tree.tag_configure("review", background="#fff3cd")

        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

    # =====================================================
    # LOADING WINDOW
    # =====================================================

    def show_loading(self):

        if self.loading_window:
            return

        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("กำลังประมวลผล")
        self.loading_window.geometry("460x190")
        self.loading_window.resizable(False, False)
        self.loading_window.transient(self.root)
        self.loading_window.protocol("WM_DELETE_WINDOW", lambda: None)

        frame = ttk.Frame(self.loading_window, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="กำลังประมวลผล PDF", font=("Segoe UI", 13, "bold")).pack(pady=(0, 12))

        self.progress_percent = ttk.Label(frame, text="0%")
        self.progress_percent.pack(pady=(0, 5))

        self.progress_bar = ttk.Progressbar(frame, orient="horizontal", mode="determinate", maximum=100)
        self.progress_bar.pack(fill="x")

        self.loading_status = ttk.Label(frame, text="กำลังเริ่มต้น...")
        self.loading_status.pack(pady=(10, 0))

        self.loading_window.update_idletasks()

        width, height = 460, 190
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.loading_window.geometry(f"{width}x{height}+{x}+{y}")

        self.loading_window.grab_set()

    def update_loading(self, percent, text):

        def update():
            if not self.loading_window:
                return
            percent_clamped = max(0, min(100, percent))
            self.progress_bar["value"] = percent_clamped
            self.progress_percent.config(text=f"{percent_clamped:.0f}%")
            self.loading_status.config(text=text)

        self.root.after(0, update)

    def hide_loading(self):

        if not self.loading_window:
            return

        try:
            self.loading_window.grab_release()
        except Exception:
            pass

        try:
            self.loading_window.destroy()
        except Exception:
            pass

        self.loading_window = None
        self.progress_bar = None
        self.progress_percent = None
        self.loading_status = None

    def set_buttons(self, state):

        self.pdf_button.config(state=state)
        self.settings_button.config(state=state)

        if self.rows:
            self.export_button.config(state=state)
        else:
            self.export_button.config(state="disabled")

    # =====================================================
    # OPEN PDF
    # =====================================================

    def open_pdf(self):

        path = filedialog.askopenfilename(
            title="เลือก Inventory Activity Standard Report",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )

        if not path:
            return

        self.show_loading()
        self.set_buttons("disabled")

        thread = threading.Thread(target=self.process_pdf_thread, args=(path,), daemon=True)
        thread.start()

    def process_pdf_thread(self, path):

        try:

            def progress(percent, text):
                self.update_loading(percent, text)

            net_sale, rows, warnings = extract_pdf(path, progress)

            self.root.after(0, lambda: self.pdf_success(net_sale, rows, warnings))

        except Exception as error:
            self.root.after(0, lambda: self.pdf_error(str(error)))

    def pdf_success(self, net_sale, rows, warnings):

        self.net_sale = net_sale
        self.rows = rows

        self.refresh_main_table()

        self.info.config(
            text=(
                f"Net Sale: {self.net_sale:,.2f} | "
                f"พบ {len(self.rows)} รายการ | "
                f"Default: {column_text(self.default_column)}"
            )
        )

        self.hide_loading()
        self.set_buttons("normal")

        if warnings:
            preview = "\n".join(warnings[:15])
            more = f"\n... และอีก {len(warnings) - 15} รายการ" if len(warnings) > 15 else ""
            messagebox.showwarning(
                "มีบางรายการที่ควรตรวจสอบด้วยตนเอง",
                (
                    f"พบ {len(warnings)} รายการที่รูปแบบข้อความใน PDF ผิดปกติ "
                    "(อาจเกิดจากค่าตัวเลขถูกตัดขึ้นบรรทัดใหม่ในตำแหน่งที่คาดเดายาก)\n\n"
                    "รายการเหล่านี้จะถูกไฮไลต์สีเหลืองในตาราง กรุณาเทียบกับ PDF ต้นฉบับ\n\n"
                    f"{preview}{more}"
                )
            )

    def pdf_error(self, error):

        self.hide_loading()
        self.set_buttons("normal")
        messagebox.showerror("อ่าน PDF ไม่สำเร็จ", error)

    # =====================================================
    # GET COLUMN FOR ROW
    # =====================================================

    def get_row_column(self, row_index):

        key = str(row_index)

        if key in self.item_settings:
            try:
                column = int(self.item_settings[key])
                if 1 <= column <= NUM_COLS:
                    return column
            except Exception:
                pass

        return self.default_column

    # =====================================================
    # CALCULATE ROW
    # =====================================================

    def calculate_row(self, row_index):

        row = self.rows[row_index]
        values = row["values"]
        column = self.get_row_column(row_index)
        index = column - 1

        selected_value = values[index] if index < len(values) else 0.0

        result = selected_value * 10000 / self.net_sale

        return selected_value, result, column

    # =====================================================
    # REFRESH MAIN TABLE
    # =====================================================

    def refresh_main_table(self):

        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.rows:
            return

        for index, row in enumerate(self.rows):

            value, result, column = self.calculate_row(index)

            tags = ("review",) if row.get("needs_review") else ()

            self.tree.insert(
                "", "end", iid=str(index),
                values=(
                    index + 1,
                    row["code"],
                    row["description"],
                    f"{value:,.2f}",
                    f"{result:,.2f}",
                    "⚠ ตรวจสอบ" if row.get("needs_review") else "",
                ),
                tags=tags
            )

    # =====================================================
    # SETTINGS WINDOW
    # =====================================================

    def open_settings(self):

        window = tk.Toplevel(self.root)
        window.title("ตั้งค่าการคำนวณ")
        window.geometry("1050x680")
        window.minsize(880, 550)
        window.transient(self.root)

        top = ttk.Frame(window, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="⚙ ตั้งค่าการคำนวณ", font=("Segoe UI", 16, "bold")).pack(anchor="w")

        ttk.Label(
            top,
            text="มี 2 แบบ: เปลี่ยนทั้งหมด หรือเปลี่ยนเฉพาะรายการที่เลือก"
        ).pack(anchor="w", pady=(4, 10))

        all_frame = ttk.LabelFrame(window, text="1. เปลี่ยนทั้งหมด", padding=12)
        all_frame.pack(fill="x", padx=12, pady=(0, 10))

        ttk.Label(all_frame, text="คอลัมน์:").pack(side="left")

        all_var = tk.StringVar()
        all_combo = ttk.Combobox(
            all_frame, textvariable=all_var,
            values=[column_text(n) for n in range(1, NUM_COLS + 1)],
            state="readonly", width=32
        )
        all_combo.set(column_text(self.default_column))
        all_combo.pack(side="left", padx=8)

        single_frame = ttk.LabelFrame(window, text="2. เปลี่ยนเฉพาะรายการ", padding=12)
        single_frame.pack(fill="both", expand=True, padx=12)

        table_frame = ttk.Frame(single_frame)
        table_frame.pack(fill="both", expand=True)

        columns = ("no", "code", "desc", "column")

        settings_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        settings_tree.heading("no", text="ลำดับ")
        settings_tree.heading("code", text="Item Code")
        settings_tree.heading("desc", text="Description")
        settings_tree.heading("column", text="คอลัมน์ที่ใช้")

        settings_tree.column("no", width=55, anchor="center")
        settings_tree.column("code", width=110)
        settings_tree.column("desc", width=440)
        settings_tree.column("column", width=200, anchor="center")

        settings_tree.pack(side="left", fill="both", expand=True)

        settings_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=settings_tree.yview)
        settings_scroll.pack(side="right", fill="y")
        settings_tree.configure(yscrollcommand=settings_scroll.set)

        def refresh_settings_table():

            for item in settings_tree.get_children():
                settings_tree.delete(item)

            for index, row in enumerate(self.rows):
                column = self.get_row_column(index)
                settings_tree.insert(
                    "", "end", iid=str(index),
                    values=(index + 1, row["code"], row["description"], column_text(column))
                )

        refresh_settings_table()

        edit_frame = ttk.Frame(single_frame, padding=(0, 10, 0, 0))
        edit_frame.pack(fill="x")

        ttk.Label(edit_frame, text="คอลัมน์:").pack(side="left")

        single_var = tk.StringVar()
        single_combo = ttk.Combobox(
            edit_frame, textvariable=single_var,
            values=[column_text(n) for n in range(1, NUM_COLS + 1)],
            state="readonly", width=32
        )
        single_combo.set(column_text(self.default_column))
        single_combo.pack(side="left", padx=8)

        def selected_item():
            selection = settings_tree.selection()
            if not selection:
                return None
            return int(selection[0])

        def load_selected(event=None):
            index = selected_item()
            if index is None:
                return
            column = self.get_row_column(index)
            single_combo.set(column_text(column))

        settings_tree.bind("<<TreeviewSelect>>", load_selected)

        def change_all():

            column = get_column_from_combo(all_combo.get())

            answer = messagebox.askyesno(
                "ยืนยัน",
                f"ต้องการเปลี่ยนทุก Item เป็น\n\n{column_text(column)}\n\nหรือไม่?",
                parent=window
            )

            if not answer:
                return

            self.default_column = column
            self.item_settings.clear()

            self.settings["default_column"] = column
            self.settings["items"] = {}
            save_settings(self.settings)

            self.refresh_main_table()
            refresh_settings_table()

            self.info.config(
                text=(
                    f"Net Sale: {self.net_sale:,.2f} | "
                    f"พบ {len(self.rows)} รายการ | "
                    f"Default: {column_text(column)}"
                )
            )

            messagebox.showinfo("สำเร็จ", f"เปลี่ยนทุก Item แล้ว\n\n{column_text(column)}", parent=window)

        ttk.Button(all_frame, text="เปลี่ยนทั้งหมด", command=change_all).pack(side="left", padx=8)

        def change_single():

            index = selected_item()

            if index is None:
                messagebox.showwarning("ยังไม่ได้เลือก", "กรุณาเลือกรายการที่ต้องการเปลี่ยน", parent=window)
                return

            column = get_column_from_combo(single_combo.get())

            self.item_settings[str(index)] = column

            self.settings["default_column"] = self.default_column
            self.settings["items"] = self.item_settings
            save_settings(self.settings)

            self.refresh_main_table()
            refresh_settings_table()

            settings_tree.selection_set(str(index))
            settings_tree.focus(str(index))

            messagebox.showinfo(
                "สำเร็จ",
                f"ลำดับ {index + 1}\n{self.rows[index]['code']}\n\nเปลี่ยนเป็น\n{column_text(column)}",
                parent=window
            )

        ttk.Button(edit_frame, text="เปลี่ยนรายการที่เลือก", command=change_single).pack(side="left", padx=8)

        bottom = ttk.Frame(window, padding=12)
        bottom.pack(fill="x")

        def reset_all():

            answer = messagebox.askyesno(
                "ยืนยัน",
                f"ต้องการรีเซ็ตการตั้งค่าทั้งหมด\nกลับเป็นคอลัมน์ {DEFAULT_COLUMN} - {COLUMN_NAMES[DEFAULT_COLUMN]} หรือไม่?",
                parent=window
            )

            if not answer:
                return

            self.default_column = DEFAULT_COLUMN
            self.item_settings.clear()

            self.settings["default_column"] = DEFAULT_COLUMN
            self.settings["items"] = {}
            save_settings(self.settings)

            all_combo.set(column_text(DEFAULT_COLUMN))
            single_combo.set(column_text(DEFAULT_COLUMN))

            self.refresh_main_table()
            refresh_settings_table()

            self.info.config(
                text=(
                    f"Net Sale: {self.net_sale:,.2f} | "
                    f"พบ {len(self.rows)} รายการ | "
                    f"Default: {column_text(DEFAULT_COLUMN)}"
                )
            )

        ttk.Button(bottom, text=f"↩ รีเซ็ตทั้งหมดเป็น {DEFAULT_COLUMN}", command=reset_all).pack(side="left")
        ttk.Button(bottom, text="ปิด", command=window.destroy).pack(side="right")

    # =====================================================
    # EXPORT EXCEL
    # =====================================================

    def export_excel(self):

        if not self.rows:
            messagebox.showwarning("ยังไม่มีข้อมูล", "กรุณาเลือก PDF ก่อน")
            return

        try:

            import pandas as pd

            path = filedialog.asksaveasfilename(
                title="บันทึกผลลัพธ์",
                defaultextension=".xlsx",
                filetypes=[("Excel Workbook", "*.xlsx")],
                initialfile="Theo_10000_Result.xlsx"
            )

            if not path:
                return

            data = []

            for index, row in enumerate(self.rows):

                value, result, column = self.calculate_row(index)

                data.append({
                    "ลำดับ": index + 1,
                    "Item Code": row["code"],
                    "Description": row["description"],
                    "Item Group": row.get("group") or "",
                    "Theo Usage": value,
                    "ผลลัพธ์": result,
                    "คอลัมน์ที่ใช้": column,
                    "ชื่อคอลัมน์": COLUMN_NAMES.get(column, f"Column {column}"),
                    "ต้องตรวจสอบ": "ใช่" if row.get("needs_review") else "",
                })

            df = pd.DataFrame(data)
            df.to_excel(path, index=False)

            messagebox.showinfo("สำเร็จ", f"บันทึกไฟล์เรียบร้อยแล้ว\n\n{path}")

        except Exception as error:
            messagebox.showerror("Export ไม่สำเร็จ", str(error))


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
