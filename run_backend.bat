@echo off
echo Starting Forcust Antigravity Backend...
echo Ensure you are running this from the project root.
set PYTHONPATH=%CD%
python -m uvicorn src.api.main:app --reload --reload-dir src
pause
