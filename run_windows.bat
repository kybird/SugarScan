@echo off
rem SugarScan Windows 데스크톱 실행 배치 파일.
rem supabase.local.json(gitignore 됨)이 있으면 접속 정보를 주입해 실행하고,
rem 없으면 로컬 전용(RemoteDisabled)으로 실행된다. README "Supabase 연결" 참조.
rem 콘솔 코드 페이지 때문에 echo 문은 영어로만 쓴다.
cd /d "%~dp0"

flutter pub get
if errorlevel 1 (
    echo [SugarScan] flutter pub get failed.
    pause
    exit /b 1
)

if exist "supabase.local.json" (
    echo [SugarScan] supabase.local.json found - running with server config.
    flutter run -d windows --dart-define-from-file=supabase.local.json
) else (
    echo [SugarScan] No supabase.local.json - running local-only.
    flutter run -d windows
)

if errorlevel 1 pause
