@echo off
echo ======================================================
echo    Сброс данных пользователей для нового учебного года
echo ======================================================
echo.

rem Активация виртуального окружения, если оно существует
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    if exist ".venv\Scripts\activate.bat" (
        call .venv\Scripts\activate.bat
    )
)

rem Запуск скрипта сброса
python reset_academic_year.py

rem Если скрипт завершился с ошибкой
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Скрипт завершился с ошибкой!
    echo Проверьте лог-файлы для подробной информации.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Нажмите любую клавишу для выхода...
pause > nul 