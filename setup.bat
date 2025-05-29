@echo off
echo Starting setup...

:: Проверяем наличие Python
python --version 2>NUL
if errorlevel 1 (
    echo Python not found! Please install Python first.
    pause
    exit /b 1
)

:: Создаем виртуальное окружение
echo Creating virtual environment...
python -m venv venv

:: Активируем виртуальное окружение и устанавливаем зависимости
echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Setup completed successfully!
echo To start the bot, run start_bot.bat
pause 