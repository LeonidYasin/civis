@echo off
REM Запуск бота с прокси через системные переменные
REM Для Happ VPN используется socks5://127.0.0.1:10808

set HTTP_PROXY=socks5://127.0.0.1:10808
set HTTPS_PROXY=socks5://127.0.0.1:10808

echo Starting bot with proxy: socks5://127.0.0.1:10808
python bot_minimal.py
