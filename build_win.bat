@echo off
REM Windows .exe 빌드 스크립트
REM 사용: build_win.bat

set APP_NAME=NEXUS

echo 의존성 설치 중...
pip install -r requirements.txt

echo PyInstaller 빌드 중...
pyinstaller ^
  --onedir ^
  --windowed ^
  --name "%APP_NAME%" ^
  --clean ^
  main.py

echo.
echo 빌드 완료: dist\%APP_NAME%\%APP_NAME%.exe
echo.
echo 배포 방법: dist\%APP_NAME% 폴더 전체를 압축해서 전달하세요.
pause
