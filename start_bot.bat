@echo off
cd /d C:\Users\User\price_monitoring_bot
echo [%date% %time%] Bot starting... >> logs\bot.log 2>&1
python bot.py >> logs\bot.log 2>&1
echo [%date% %time%] Bot stopped (exit code %errorlevel%). >> logs\bot.log 2>&1
