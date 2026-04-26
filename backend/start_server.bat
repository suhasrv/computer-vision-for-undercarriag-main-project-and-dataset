@echo off
REM Start FastAPI backend server
cd /d "%~dp0"
echo Starting FastAPI Backend...
echo.
echo Activating virtual environment...
if exist "..\.venv\Scripts\activate.bat" (
	call "..\.venv\Scripts\activate.bat"
) else (
	if exist "..\venv\Scripts\activate.bat" (
		call "..\venv\Scripts\activate.bat"
	) else (
		if exist "venv\Scripts\activate.bat" (
			call "venv\Scripts\activate.bat"
		) else (
			echo WARNING: No virtual environment activation script found.
			echo Create one at the project root named .venv (recommended) or venv, or activate manually.
		)
	)
)
echo.
echo Starting server on http://127.0.0.1:8000
echo Press Ctrl+C to stop
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
