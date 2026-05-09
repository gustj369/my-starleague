@echo off
chcp 65001 > nul
echo.
echo [빌드] LegendLeague.exe 빌드 시작...
echo =====================================================

REM Python 실행 파일 경로 설정
REM %LOCALAPPDATA% = C:\Users\{사용자명}\AppData\Local  (환경 변수, 사용자명 하드코딩 없음)
REM 다른 Python 경로를 사용할 경우 아래 한 줄만 수정하세요
set PYTHON=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe

"%PYTHON%" -m PyInstaller my_starleague.spec --noconfirm

echo =====================================================
if %errorlevel%==0 (
    echo [성공] dist\LegendLeague.exe 생성 완료
) else (
    echo [실패] 빌드 실패 - 위 로그를 확인하세요
    echo        Python 경로를 확인하세요: %PYTHON%
)
echo.
pause
