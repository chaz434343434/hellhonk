@echo off
cd /d "%~dp0"
py -3.9 -W ignore hellhonk.py
if errorlevel 1 pause
