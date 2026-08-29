@echo off
setlocal
title Build Theo x 10,000 Calculator
echo Installing build requirements...
py -m pip install --upgrade pyinstaller pdfplumber pandas openpyxl
if errorlevel 1 goto FAIL
echo.
echo Building EXE...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name "Theo_10000_Calculator" "Theo_10000_Calculator.py"
if errorlevel 1 goto FAIL
echo.
echo ==========================================
echo BUILD COMPLETE
echo EXE: dist\Theo_10000_Calculator.exe
echo ==========================================
pause
exit /b 0
:FAIL
echo.
echo BUILD FAILED
pause
exit /b 1
