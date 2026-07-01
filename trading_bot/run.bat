@echo off
REM Lance le bot Telegram (Windows)
cd /d "%~dp0\.."

if not exist "trading_bot\.env" (
    echo.
    echo ERREUR: trading_bot\.env introuvable.
    echo Copiez trading_bot\.env.example vers trading_bot\.env
    echo puis mettez votre TELEGRAM_BOT_TOKEN dedans.
    echo.
    pause
    exit /b 1
)

echo Installation des dependances...
pip install -q -r trading_bot\requirements.txt

echo Demarrage du bot...
python -m trading_bot.main
pause
