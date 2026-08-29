THEO x 10,000 CALCULATOR - Windows EXE

วิธีที่ 1: สร้าง EXE บน Windows
1. ติดตั้ง Python 3.11+ ชั่วคราวบนเครื่องสำหรับ "สร้าง" โปรแกรม
2. ดับเบิลคลิก build_windows.bat
3. รอจนเสร็จ
4. ไฟล์ใช้งานจริงอยู่ที่ dist\Theo_10000_Calculator.exe
5. สามารถเอา EXE ไปใช้บนเครื่อง Windows อื่นได้ โดยไม่ต้องติดตั้ง Python

วิธีที่ 2: ไม่ต้องติดตั้ง Python เลย
- อัปโหลดโฟลเดอร์นี้เข้า GitHub repository
- GitHub Actions จะ build Windows EXE ให้
- workflow อยู่ที่ .github\workflows\build-windows.yml

การทำงาน:
PDF -> อ่าน Net Sale -> อ่าน Theo Usage -> Theo * 10000 / Net Sale -> แสดงผล

THEO × 10,000 CALCULATOR – Windows EXE

A Windows desktop application for calculating:

Theo Usage × 10,000 ÷ Net Sale

Method 1: Build the EXE on Windows

1. Install Python 3.11 or later temporarily on the computer used to build the application.
2. Double-click "build_windows.bat".
3. Wait until the build process is complete.
4. The final executable will be available at:

dist\Theo_10000_Calculator.exe

5. Copy the ".exe" file to another Windows computer and run it.

Python does not need to be installed on the computer that runs the EXE.

---

Method 2: Build Without Installing Python

You can build the Windows EXE using GitHub Actions without installing Python locally.

1. Upload this project folder to a GitHub repository.
2. GitHub Actions will automatically build the Windows EXE.
3. The workflow configuration is located at:

.github\workflows\build-windows.yml

4. After the workflow finishes, download the generated Windows EXE from the GitHub Actions Artifacts or Release.

---

How It Works

PDF
 ↓
Read Net Sale
 ↓
Read Theo Usage
 ↓
Theo Usage × 10,000 ÷ Net Sale
 ↓
Display Result

Main Features

- Read data directly from PDF reports
- Extract Net Sale
- Extract Theo Usage
- Calculate Theo Usage × 10,000 ÷ Net Sale
- Display the calculation results
- Export results to Excel
- Windows standalone EXE
- No Python installation required on the target computer
- Settings for selecting the data column
- Loading screen and progress indicator during PDF processing
