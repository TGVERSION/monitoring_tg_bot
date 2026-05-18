@echo off
cd /d C:\Users\User\price_monitoring_bot
echo [%date% %time%] Sync starting... >> logs\sync_supabase.log 2>&1
python sync_to_supabase.py
echo [%date% %time%] Sync finished (exit code %errorlevel%). >> logs\sync_supabase.log 2>&1
