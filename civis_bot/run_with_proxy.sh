#!/bin/bash
# Запуск бота с прокси через системные переменные
# Для Happ VPN используется socks5://127.0.0.1:10808

export HTTP_PROXY=socks5://127.0.0.1:10808
export HTTPS_PROXY=socks5://127.0.0.1:10808

echo "Starting bot with proxy: socks5://127.0.0.1:10808"
python3 bot_minimal.py
