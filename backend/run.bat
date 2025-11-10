@echo off
cd %~dp0
python -m uvicorn main:app --reload --port 8000

