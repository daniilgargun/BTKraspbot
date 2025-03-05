@echo off
:start
echo Starting bot...
call venv\Scripts\activate
python -m bot.main
if errorlevel 1 (
    echo Bot crashed, restarting in 60 seconds...
    timeout /t 60
    goto start
)
pause 