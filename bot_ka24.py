import os
import sys
import time

print("🚀 ТЕСТОВЫЙ БОТ ЗАПУЩЕН", flush=True)
print(f"PYTHONPATH: {sys.path}", flush=True)

# Проверяем переменные окружения
print("\n🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ:", flush=True)
print(f"VK_TOKEN: {'✅ есть' if os.getenv('VK_TOKEN') else '❌ нет'}", flush=True)
print(f"GROUP_ID: {'✅ есть' if os.getenv('GROUP_ID') else '❌ нет'}", flush=True)
print(f"ADMIN_VK_ID: {'✅ есть' if os.getenv('ADMIN_VK_ID') else '❌ нет'}", flush=True)
print(f"GOOGLE_CREDENTIALS_JSON: {'✅ есть' if os.getenv('GOOGLE_CREDENTIALS_JSON') else '❌ нет'}", flush=True)

if os.getenv('GOOGLE_CREDENTIALS_JSON'):
    creds = os.getenv('GOOGLE_CREDENTIALS_JSON')
    print(f"Длина JSON: {len(creds)} символов", flush=True)
    print(f"Первые 100 символов: {creds[:100]}...", flush=True)

print("\n✅ Тестовый бот успешно запущен и работает", flush=True)
print("📌 Бот будет работать 60 секунд, затем завершится", flush=True)

# Держим бот живым 60 секунд, чтобы можно было увидеть логи
time.sleep(60)
print("⏹️ Тестовый бот завершает работу", flush=True)
