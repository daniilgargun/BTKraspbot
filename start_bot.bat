@echo off
:: Активируем виртуальное окружение
call venv\Scripts\activate.bat

:: Запускаем бота
python bot/main.py

:: Если бот завершился с ошибкой, не закрываем окно
if errorlevel 1 (
    echo Bot stopped with error!
    pause
) 