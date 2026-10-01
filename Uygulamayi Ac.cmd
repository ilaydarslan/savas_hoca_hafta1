@echo off
chcp 65001 >nul
title Müşterek - Uygulamayi Ac
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0peer-decision-system\start-demo.ps1"
if errorlevel 1 (
  echo.
  echo Uygulama acilirken hata olustu. Yukaridaki hata mesajini kontrol edin.
  pause
)
