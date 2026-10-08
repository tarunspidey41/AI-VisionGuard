@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo =============================================
echo       AI VISIONGUARD - PYTHON 3.14 SETUP
echo =============================================

echo.
echo [1/5] Checking Python 3.14...
py -3.14 -c "import sys; print(sys.version); print('Free-threaded:', hasattr(sys,'_is_gil_enabled') and not sys._is_gil_enabled())" > .python_check.txt 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Regular Python 3.14 was not found with the Python Launcher.
  echo Install regular CPython 3.14, not Python 3.14t/free-threaded.
  echo.
  type .python_check.txt
  del .python_check.txt >nul 2>&1
  pause
  exit /b 1
)
type .python_check.txt
findstr /C:"Free-threaded: True" .python_check.txt >nul
if not errorlevel 1 (
  echo.
  echo ERROR: The selected Python 3.14 is FREE-THREADED 3.14t.
  echo AI VisionGuard should use regular CPython 3.14 because some native
  echo AI dependencies do not provide compatible free-threaded wheels.
  echo.
  echo Use: py -3.14 -m venv .venv
  echo NOT: py -3.14t -m venv .venv
  del .python_check.txt >nul 2>&1
  pause
  exit /b 1
)
del .python_check.txt >nul 2>&1

if exist .venv (
  echo.
  echo [2/5] Reusing existing virtual environment...
) else (
  echo.
  echo [2/5] Creating virtual environment with regular Python 3.14...
  py -3.14 -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create the virtual environment.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo ERROR: Could not activate .venv.
  pause
  exit /b 1
)

python -c "import sys; print('Virtual environment:', sys.executable); print('Python:', sys.version)"

 echo.
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 goto :install_failed

echo.
echo [4/5] Installing Python 3.14-compatible dependencies...
echo This uses wheels only, so pip will NOT try to compile Rust/C++ packages.
python -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto :install_failed

echo.
echo [5/5] Starting VisionGuard...
echo Opening http://127.0.0.1:8000
start "AI VisionGuard Server" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8000
exit /b 0

:install_failed
echo.
echo =============================================
echo DEPENDENCY INSTALLATION FAILED
echo =============================================
echo.
echo The installer was configured to use Python 3.14 wheels only.
echo If you see a package ending in "-runtime-32" trying to build with Cargo,
echo you are almost certainly using Python 3.14t/free-threaded or an outdated pip.
echo.
echo Check with:
echo   py -0p
 echo   .venv\Scripts\python.exe --version
pause
exit /b 1
