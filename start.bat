@echo off
REM Скрипт быстрого запуска Streamlit-приложения для анализа углеводородов
REM Для Windows

echo Запуск приложения для анализа стабильности углеводородов...
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден в системе!
    echo Пожалуйста, установите Python 3.8 или выше.
    pause
    exit /b 1
)

REM Проверка наличия установленных зависимостей
echo Проверка зависимостей...
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Зависимости не установлены. Установка...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ОШИБКА: Не удалось установить зависимости!
        pause
        exit /b 1
    )
)

echo.
echo Запуск Streamlit-приложения...
echo Приложение откроется в вашем браузере по адресу: http://localhost:8501
echo.
echo Для остановки приложения нажмите Ctrl+C в этом окне.
echo.

REM Запуск приложения
streamlit run app.py

pause
