@echo off
chcp 65001 > nul
echo.
echo [빌드] LegendLeague.exe 빌드 시작...
echo =====================================================

C:\Users\gustj\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe my_starleague.spec --noconfirm

echo =====================================================
if %errorlevel%==0 (
    echo [성공] dist\LegendLeague.exe 생성 완료
) else (
    echo [실패] 빌드 실패 - 위 로그를 확인하세요
)
echo.
pause
