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
