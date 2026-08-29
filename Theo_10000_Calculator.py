import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pdfplumber


APP_TITLE = "Theo 10000 Calculator"


def parse_number(value):
    """แปลงข้อความตัวเลข เช่น 1,234.50 หรือ (10.00) เป็นตัวเลข"""
    value = value.replace(",", "").strip()

    if not value:
        return 0.0

    if value.startswith("(") and value.endswith(")"):
        return -float(value[1:-1])

    return float(value)


def extract_pdf(pdf_path):
    """อ่านข้อมูลจาก Inventory Activity Standard Report"""

    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += "\n" + page_text

    # --------------------------------------------------
    # หา Net Sale
    # --------------------------------------------------

    net_sale_match = re.search(
        r"Net\s+Sale\s+([\d,]+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if not net_sale_match:
        raise ValueError("ไม่พบ Net Sale ใน PDF")

    net_sale = parse_number(net_sale_match.group(1))

    if net_sale == 0:
        raise ValueError("Net Sale เป็น 0 ไม่สามารถคำนวณได้")

    # --------------------------------------------------
    # แยกบรรทัด
    # --------------------------------------------------

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    rows = []

    # --------------------------------------------------
    # หา Item Code
    # ตัวอย่าง THK0002 / THF2100
    # --------------------------------------------------

    item_code_pattern = re.compile(
        r"^TH[A-Z0-9]+$",
        re.IGNORECASE
    )

    stop_words = (
        "Sub Total:",
        "Item Group:",
        "Total All Item Groups",
        "QSA -"
    )

    i = 0

    while i < len(lines):

        current_line = lines[i]
        clean_line = current_line.replace(" ", "")

        if not item_code_pattern.fullmatch(clean_line):
            i += 1
            continue

        code = clean_line.upper()

        # --------------------------------------------------
        # เก็บข้อมูลหลัง Item Code
        # --------------------------------------------------

        block = []
        j = i + 1

        while j < len(lines):

            next_line = lines[j]
            next_clean = next_line.replace(" ", "")

            # เจอ Item Code ตัวใหม่
            if item_code_pattern.fullmatch(next_clean):
                break

            # เจอหัวข้อที่ไม่ใช่ข้อมูลสินค้า
            if next_line.startswith(stop_words):
                break

            block.append(next_line)

            combined = " ".join(block)

            # ตรวจจำนวนตัวเลข
            number_matches = re.findall(
                r"?-?\d[\d,]*(?:\.\d+)??",
                combined
            )

            # แถวข้อมูลปกติมีตัวเลขจำนวนมาก
            if len(number_matches) >= 12:
                break

            j += 1

        block_text = " ".join(block)

        # --------------------------------------------------
        # ดึงตัวเลข
        # --------------------------------------------------

        number_matches = re.findall(
            r"?-?\d[\d,]*(?:\.\d+)??",
            block_text
        )

        if len(number_matches) >= 8:

            try:

                values = [
                    parse_number(x)
                    for x in number_matches
                ]

                # ลำดับข้อมูล:
                #
                # 0 = Opening
                # 1 = Purchases
                # 2 = Return
                # 3 = Transfer In
                # 4 = Transfer Out
                # 5 = Closing
                # 6 = Act. Usage
                # 7 = Theo. Usage

                theo_usage = values[7]

                # --------------------------------------------------
                # สูตร
                #
                # Theo Usage × 10,000 ÷ Net Sale
                #
                # ผลลัพธ์เป็น "ตัวเลข"
                # ไม่ใช่เปอร์เซ็นต์
                # --------------------------------------------------

                theo_result = (
                    theo_usage * 10000
                ) / net_sale

                # --------------------------------------------------
                # Description
                # --------------------------------------------------

                desc_match = re.match(
                    r"^(.*?)(?=?-?\d[\d,]*(?:\.\d+)??)",
                    block_text
                )

                if desc_match:
                    description = desc_match.group(1).strip()
                else:
                    description = block_text

                # ล้าง Description ที่ไม่จำเป็น
                description = description.strip()

                if description:

                    rows.append(
                        (
                            code,
                            description,
                            theo_usage,
                            theo_result
