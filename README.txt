THEO × 10,000 CALCULATOR

โปรแกรมคำนวณ Theo Usage × 10,000 ÷ Net Sale สำหรับ Windows
A Windows desktop application for calculating Theo Usage × 10,000 ÷ Net Sale.

---

🇹🇭 ภาษาไทย

📌 เกี่ยวกับโปรแกรม

THEO × 10,000 CALCULATOR เป็นโปรแกรมสำหรับอ่านข้อมูลจากไฟล์ PDF รายงาน Inventory Activity Standard Report และนำค่า Theo Usage มาคำนวณตามสูตร:

«Theo Usage × 10,000 ÷ Net Sale»

โปรแกรมช่วยลดการคำนวณด้วยตนเองและสามารถส่งออกผลลัพธ์เป็นไฟล์ Excel ได้

---

✨ คุณสมบัติ

- 📄 อ่านข้อมูลจาก PDF
- 💰 อ่านค่า Net Sale
- 📊 อ่านค่า Theo Usage
- 🧮 คำนวณ "Theo Usage × 10,000 ÷ Net Sale"
- 📋 แสดงผลลัพธ์ในตาราง
- ⚙️ สามารถเลือกคอลัมน์ที่ต้องการนำมาคำนวณได้
- 🔢 สามารถตั้งค่าคอลัมน์เริ่มต้นได้
- 🎯 สามารถเปลี่ยนคอลัมน์เฉพาะรายการได้
- 🔄 สามารถเปลี่ยนคอลัมน์ทั้งหมดได้
- 📊 Export ผลลัพธ์เป็น Excel
- ⏳ มี Loading และ Progress ระหว่างอ่าน PDF
- 🧵 ใช้ Thread เพื่อไม่ให้หน้าต่างโปรแกรมค้างระหว่างประมวลผล
- 🪟 รองรับ Windows
- 🐍 เครื่องที่ใช้โปรแกรม ".exe" ไม่จำเป็นต้องติดตั้ง Python

---

🧮 การทำงาน

PDF
 ↓
อ่าน Net Sale
 ↓
อ่าน Theo Usage
 ↓
Theo Usage × 10,000 ÷ Net Sale
 ↓
แสดงผลลัพธ์

ตัวอย่าง

หาก:

Net Sale = 10,000
Theo Usage = 250

โปรแกรมจะคำนวณ:

250 × 10,000 ÷ 10,000
= 250

---

🛠️ วิธี Build Windows EXE

วิธีที่ 1: Build บน Windows

1. ติดตั้ง Python

ติดตั้ง Python 3.11 หรือใหม่กว่า บนเครื่องที่ใช้สำหรับ Build โปรแกรม

«Python จำเป็นเฉพาะเครื่องที่ใช้ Build เท่านั้น»

2. Build โปรแกรม

ดับเบิลคลิกไฟล์:

build_windows.bat

3. รอจน Build เสร็จ

เมื่อ Build สำเร็จ ไฟล์โปรแกรมจะอยู่ที่:

dist\Theo_10000_Calculator.exe

4. นำไปใช้งาน

สามารถนำไฟล์:

Theo_10000_Calculator.exe

ไปใช้งานบนเครื่อง Windows เครื่องอื่นได้

เครื่องปลายทางไม่จำเป็นต้องติดตั้ง Python

---

☁️ วิธีที่ 2: Build ด้วย GitHub Actions

สามารถ Build Windows EXE โดยไม่ต้องติดตั้ง Python บนเครื่องของคุณ

ขั้นตอน

1. Upload โปรเจกต์ทั้งหมดขึ้น GitHub Repository
2. GitHub Actions จะทำการ Build โปรแกรมโดยอัตโนมัติ
3. Workflow อยู่ที่:

.github\workflows\build-windows.yml

4. เมื่อ Build เสร็จ สามารถดาวน์โหลดไฟล์ EXE จาก:

GitHub Actions → Artifacts

หรือจาก GitHub Release หากตั้งค่า Workflow ให้สร้าง Release

---

📁 โครงสร้างโปรเจกต์

Theo-10000-Calculator/
│
├── Theo_10000_Calculator.py
├── build_windows.bat
├── requirements.txt
├── README.md
│
└── .github/
    └── workflows/
        └── build-windows.yml

---

⚙️ การตั้งค่าคอลัมน์

โปรแกรมรองรับการเลือกคอลัมน์สำหรับใช้คำนวณ

ค่าเริ่มต้น:

8 - Theo. Usage

สามารถเลือกได้ทั้ง:

เปลี่ยนทั้งหมด

เปลี่ยนคอลัมน์ที่ใช้คำนวณสำหรับทุกรายการพร้อมกัน

เปลี่ยนเฉพาะรายการ

สามารถเลือกเฉพาะรายการ เช่น:

ลำดับ 5 → คอลัมน์ 7 - Act. Usage

โดยรายการอื่นจะยังคงใช้ค่าที่ตั้งไว้เดิม

---

📊 Export Excel

สามารถ Export ผลลัพธ์ออกเป็น:

Theo_10000_Result.xlsx

โดยมีข้อมูล เช่น:

- ลำดับ
- Item Code
- Description
- Item Group
- ค่าที่ใช้คำนวณ
- ผลลัพธ์
- คอลัมน์ที่ใช้
- ชื่อคอลัมน์
- สถานะการตรวจสอบ

---

💻 ระบบที่รองรับ

- Windows 10
- Windows 11

สำหรับการ Build:

Python 3.11+
PyInstaller

---

⚠️ หมายเหตุ

โปรแกรมออกแบบมาสำหรับ PDF ที่มีโครงสร้างข้อมูลตรงกับ Inventory Activity Standard Report ที่รองรับโดยโปรแกรม

หากรูปแบบ PDF แตกต่างจากรายงานที่รองรับ อาจทำให้ข้อมูลบางรายการถูกอ่านไม่ถูกต้อง ควรตรวจสอบผลลัพธ์กับ PDF ต้นฉบับก่อนนำไปใช้งานจริง

---

<br>🇬🇧 English

📌 About

THEO × 10,000 CALCULATOR is a Windows desktop application that reads data from an Inventory Activity Standard Report PDF and calculates:

«Theo Usage × 10,000 ÷ Net Sale»

The application helps reduce manual calculations and allows users to export the results to Excel.

---

✨ Features

- 📄 Read data directly from PDF
- 💰 Extract Net Sale
- 📊 Extract Theo Usage
- 🧮 Calculate "Theo Usage × 10,000 ÷ Net Sale"
- 📋 Display calculation results
- ⚙️ Select which column should be used for calculation
- 🔢 Set a default calculation column
- 🎯 Override the column for individual items
- 🔄 Change the calculation column for all items
- 📊 Export results to Excel
- ⏳ Loading screen with progress percentage
- 🧵 Background processing using Thread
- 🪟 Windows desktop application
- 🐍 Python is not required on the computer running the EXE

---

🧮 How It Works

PDF
 ↓
Read Net Sale
 ↓
Read Theo Usage
 ↓
Theo Usage × 10,000 ÷ Net Sale
 ↓
Display Result

Example

If:

Net Sale = 10,000
Theo Usage = 250

The application calculates:

250 × 10,000 ÷ 10,000
= 250

---

🛠️ Build Windows EXE

Method 1: Build on Windows

1. Install Python

Install Python 3.11 or later on the computer used to build the application.

«Python is only required on the build computer.»

2. Build the application

Double-click:

build_windows.bat

3. Wait for the build to finish

After a successful build, the executable will be located at:

dist\Theo_10000_Calculator.exe

4. Run the application

Copy:

Theo_10000_Calculator.exe

to another Windows computer and run it.

Python does not need to be installed on the target computer.

---

☁️ Method 2: Build with GitHub Actions

You can build the Windows EXE without installing Python locally.

Steps

1. Upload the entire project to a GitHub Repository.
2. GitHub Actions will automatically build the Windows EXE.
3. The workflow is located at:

.github\workflows\build-windows.yml

4. When the workflow finishes, download the EXE from:

GitHub Actions → Artifacts

or from the GitHub Release if the workflow is configured to create a Release.

---

📁 Project Structure

Theo-10000-Calculator/
│
├── Theo_10000_Calculator.py
├── build_windows.bat
├── requirements.txt
├── README.md
│
└── .github/
    └── workflows/
        └── build-windows.yml

---

⚙️ Column Settings

The application allows users to select which report column should be used for calculation.

Default:

8 - Theo. Usage

Two setting modes are available:

Change All

Change the calculation column for all items at once.

Change Individual Item

Change the calculation column for only one selected item.

For example:

Item 5 → Column 7 - Act. Usage

Other items will keep their existing settings.

---

📊 Export to Excel

The application can export calculation results to:

Theo_10000_Result.xlsx

The exported file can include:

- Item Number
- Item Code
- Description
- Item Group
- Selected Value
- Result
- Selected Column
- Column Name
- Review Status

---

💻 Supported Systems

- Windows 10
- Windows 11

Build requirements:

Python 3.11+
PyInstaller

---

⚠️ Notes

This application is designed for PDF files following the supported Inventory Activity Standard Report structure.

If the PDF layout differs from the supported report format, some values may be extracted incorrectly. Always verify the results against the original PDF before using the data for actual operations.

---

📜 License

This project is provided for its intended use with supported Inventory Activity Standard Reports.
