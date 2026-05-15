import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.upload import VkUpload
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import random
import re
import os
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
import json


# ===== ОТЛАДКА GOOGLE CREDENTIALS =====
import os
print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ:")
print(f"VK_TOKEN: {'✅ есть' if os.getenv('VK_TOKEN') else '❌ нет'}")
print(f"GROUP_ID: {'✅ есть' if os.getenv('GROUP_ID') else '❌ нет'}")
print(f"GOOGLE_CREDENTIALS_JSON: {'✅ есть' if os.getenv('GOOGLE_CREDENTIALS_JSON') else '❌ нет'}")

if os.getenv('GOOGLE_CREDENTIALS_JSON'):
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    print(f"Длина JSON: {len(creds_json)} символов")
    print(f"Начинается с: {creds_json[:50]}...")
    
# ===== ЗАГРУЗКА ТОКЕНОВ ИЗ .env ФАЙЛА =====
load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_VK_ID = int(os.getenv("ADMIN_VK_ID"))

# Проверка, что переменные загрузились
if not VK_TOKEN:
    print("❌ ОШИБКА: Не удалось загрузить VK_TOKEN из .env файла!")
    exit(1)
print("✅ Токены успешно загружены из .env файла")

# ===== ПУТИ К ФОТО =====
PHOTO_PRICES = "prices.jpg"
PHOTO_SCHEDULE = "schedule.jpg"
PHOTO_CONTACTS = "contacts.jpg"

# ===== ДАННЫЕ РАСПИСАНИЯ =====
SCHEDULE = {
    "Lady Dance": {"Дарья": ["Понедельник 11:00", "Среда 11:00"]},
    "Stretching": {"Дарья": ["Понедельник 12:00", "Среда 12:00"]},
    "Hip Hop 9+": {"Вика": ["Понедельник 19:00", "Среда 19:00"]},
    "Strip": {
        "Оля": ["Понедельник 19:00", "Среда 19:00"],
        "Катя": ["Понедельник 20:00", "Пятница 19:00"]
    },
    "Jazz Funk 12+": {"Вика": ["Понедельник 20:00", "Вторник 19:00", "Среда 20:00", "Четверг 19:00"]},
    "Lady Bachata": {"Даша": ["Вторник 12:00", "Среда 20:00"]},
    "Stretching 10+": {"Аня": ["Вторник 19:00", "Четверг 19:00"]},
    "Stretching + силовая": {"Аня": ["Вторник 20:00", "Четверг 20:00"]},
    "Dancehall": {"Катерина": ["Вторник 20:00", "Четверг 20:00"]},
    "High Heels": {
        "Катерина": ["Вторник 21:00", "Четверг 21:00"],
        "Катя": ["Суббота 14:00"]
    },
    "Сальса": {"Энмануэль": ["Вторник 21:00", "Четверг 21:00"]},
    "Girly Choreo 12+": {"Соня": ["Четверг 17:00"]},
    "Парная Бачата": {"Паша и Даша": ["Пятница 20:00"]},
    "Hip Hop 14+": {"Дима": ["Суббота 14:30"]},
    "Girly Hip Hop 14+": {"Настя": ["Суббота 15:30"]}
}

# ===== РАЗДЕЛЕНИЕ НА СПИСКИ =====
KIDS_DIRECTIONS_1 = ["Hip Hop 9+", "Jazz Funk 12+", "Stretching 10+"]
KIDS_DIRECTIONS_2 = ["Girly Choreo 12+", "Hip Hop 14+", "Girly Hip Hop 14+"]

ADULTS_DIRECTIONS_1 = ["Stretching", "Strip", "Stretching + силовая", "Dancehall", "High Heels"]
ADULTS_DIRECTIONS_2 = ["Lady Dance", "Lady Bachata", "Сальса", "Парная Бачата"]

WEEKDAYS_FULL = {
    "Понедельник": 0, "Вторник": 1, "Среда": 2, 
    "Четверг": 3, "Пятница": 4, "Суббота": 5, "Воскресенье": 6
}

WEEKDAYS_SHORT = {
    "Понедельник": "Пн",
    "Вторник": "Вт", 
    "Среда": "Ср",
    "Четверг": "Чт",
    "Пятница": "Пт",
    "Суббота": "Сб",
    "Воскресенье": "Вс"
}

# ===== ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS =====
def get_sheet(sheet_name):
    """
    Загружает учетные данные Google из переменной окружения.
    На Bothost читает из GOOGLE_CREDENTIALS_JSON.
    Для локальной разработки — из файла ka24-credentials.json.
    """
    # 1. Пытаемся взять JSON из переменной окружения (Bothost)
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if creds_json_str:
        print("🔐 Загружаем Google Credentials из переменной окружения")
        # Парсим JSON-строку в словарь
        creds_dict = json.loads(creds_json_str)
        
        # ВНИМАНИЕ! В переменной окружения все переносы строк могут быть экранированы как "\\n"
        # Их нужно превратить в реальные переносы строк, иначе Google выдаст ошибку
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        
        # Создаем объект учетных данных
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return creds
    
    # 2. Если переменной окружения нет — пробуем прочитать локальный файл (для разработки)
    elif os.path.exists("ka24-credentials.json"):
        print("⚠️ Используем локальный файл ka24-credentials.json (только для разработки)")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("ka24-credentials.json", scope)
        return creds
    
    else:
        raise Exception("❌ Нет доступа к Google Sheets: нет ни GOOGLE_CREDENTIALS_JSON, ни файла ka24-credentials.json")

def get_sheet(sheet_name):
    """Возвращает нужный лист Google Sheets"""
    creds = get_google_creds()
    client = gspread.authorize(creds)
    sheet = client.open("Бот_заявки_КА24")
    return sheet.worksheet(sheet_name)

# ===== FSM =====
user_states = {}

# ===== ФУНКЦИЯ ОТПРАВКИ ФОТО =====
def send_photo(user_id, photo_path, caption=""):
    try:
        upload = VkUpload(vk)
        photo = upload.photo_messages(photos=photo_path)
        attachment = f"photo{photo[0]['owner_id']}_{photo[0]['id']}"
        vk.messages.send(
            user_id=user_id,
            message=caption,
            attachment=attachment,
            random_id=random.randint(1, 10**9)
        )
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки фото: {e}")
        return False

# ===== КЛАВИАТУРЫ =====
def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Записаться', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('Отменить запись', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Расписание', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Прайс', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Отзыв', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Контакты', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Админ', color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_category_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("🧒 Детские направления", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("👩 Взрослые направления", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Назад в меню", color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_directions_keyboard(directions_list, is_first_list, category_type):
    keyboard = VkKeyboard(one_time=True)
    for direction in directions_list:
        keyboard.add_button(direction, color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
    if category_type == 'kids':
        if is_first_list:
            keyboard.add_button("🔄 Другие детские", color=VkKeyboardColor.PRIMARY)
        else:
            keyboard.add_button("🔄 Первые детские", color=VkKeyboardColor.PRIMARY)
    else:
        if is_first_list:
            keyboard.add_button("🔄 Другие взрослые", color=VkKeyboardColor.PRIMARY)
        else:
            keyboard.add_button("🔄 Первые взрослые", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🔄 Другая категория", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Назад в меню", color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_trainers_keyboard(direction):
    keyboard = VkKeyboard(one_time=True)
    trainers = list(SCHEDULE.get(direction, {}).keys())
    for trainer in trainers:
        keyboard.add_button(trainer, color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
    keyboard.add_button("🔄 Выбрать другое направление", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Назад в меню", color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_schedule_keyboard(direction, trainer):
    keyboard = VkKeyboard(one_time=True)
    sessions = SCHEDULE.get(direction, {}).get(trainer, [])
    today = datetime.now()
    for session in sessions:
        day_name, time_str = session.rsplit(' ', 1)
        days_ahead = (WEEKDAYS_FULL[day_name] - today.weekday()) % 7
        if days_ahead == 0 and today.hour >= int(time_str.split(':')[0]):
            days_ahead = 7
        next_date = today + timedelta(days=days_ahead)
        date_str = next_date.strftime("%d.%m")
        short_day = WEEKDAYS_SHORT[day_name]
        button_text = f"{short_day} {date_str} {time_str}"
        keyboard.add_button(button_text, color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
    keyboard.add_button("✏️ Выбрать другое время", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("🔄 Выбрать другого тренера", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("◀️ Назад в меню", color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_confirmation_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("✅ Да, все верно", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("❌ Нет, нужно исправить", color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_back_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("◀️ Назад в меню", color=VkKeyboardColor.SECONDARY)
    return keyboard

def get_cancel_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("✅ Да, отменить", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("❌ Нет, оставить", color=VkKeyboardColor.POSITIVE)
    return keyboard

# ===== ОТПРАВКА СООБЩЕНИЙ =====
def send_message(user_id, text, keyboard=None):
    try:
        vk.messages.send(
            user_id=user_id,
            message=text,
            random_id=random.randint(1, 10**9),
            keyboard=keyboard.get_keyboard() if keyboard else None
        )
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения: {e}")

# ===== ПРОВЕРКА ТЕЛЕФОНА =====
def validate_phone(phone):
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits[0] == '7':
        return True, digits
    elif len(digits) == 10:
        return True, '7' + digits
    elif len(digits) == 11 and digits[0] == '8':
        return True, '7' + digits[1:]
    else:
        return False, None

# ===== ПОИСК ЗАПИСЕЙ ПОЛЬЗОВАТЕЛЯ ПО VK ID =====
def get_user_active_bookings(user_id):
    """Находит все активные записи пользователя по VK ID"""
    try:
        sheet = get_sheet("Заявки")
        records = sheet.get_all_records()
        
        active_bookings = []
        for i, record in enumerate(records, start=2):
            # Проверяем, что запись активна (статус "новая")
            if record.get('Статус', '') != 'новая':
                continue
            
            # Проверяем VK ID
            record_user_id = str(record.get('VK ID клиента', ''))
            if record_user_id == str(user_id):
                active_bookings.append({
                    'row_id': i,
                    'datetime': record.get('Дата/время занятия', 'не указано'),
                    'direction': record.get('Направление', ''),
                    'trainer': record.get('Тренер', ''),
                    'name': record.get('Имя', '')
                })
        
        return active_bookings
    except Exception as e:
        print(f"❌ Ошибка поиска записей: {e}")
        return []

def cancel_booking(row_id):
    """Отменяет запись, меняя статус на 'отменена'"""
    try:
        sheet = get_sheet("Заявки")
        sheet.update_cell(row_id, 7, "отменена")
        return True
    except Exception as e:
        print(f"❌ Ошибка отмены записи: {e}")
        return False

# ===== ОБРАБОТЧИК ГЛАВНОГО МЕНЮ =====
def handle_start(user_id, message):
    if message == 'записаться':
        user_states[user_id] = {'state': 'WAITING_CATEGORY', 'data': {}}
        send_message(user_id, "Выбери категорию занятий:", keyboard=get_category_keyboard())
    
    elif message == 'отменить запись':
        # Ищем активные записи пользователя по VK ID
        bookings = get_user_active_bookings(user_id)
        
        if not bookings:
            send_message(user_id, "❌ У вас нет активных записей.\n\nЧтобы записаться, нажмите 'Записаться'", 
                       keyboard=get_main_keyboard())
        elif len(bookings) == 1:
            # Одна запись - сразу спрашиваем подтверждение
            booking = bookings[0]
            user_states[user_id] = {
                'state': 'CANCEL_CONFIRM', 
                'data': {
                    'cancel_row_id': booking['row_id'],
                    'cancel_booking': booking
                }
            }
            booking_info = f"📅 {booking['datetime']}\n💃 {booking['direction']}\n👨‍🏫 {booking['trainer']}"
            send_message(user_id, f"🔍 У вас есть активная запись:\n\n{booking_info}\n\nОтменить её?", 
                       keyboard=get_cancel_keyboard())
        else:
            # Несколько записей - показываем список
            user_states[user_id] = {'state': 'CANCEL_SELECT', 'data': {'cancel_bookings': bookings}}
            cancel_text = "🔍 У вас есть несколько активных записей:\n\n"
            for idx, booking in enumerate(bookings, start=1):
                cancel_text += f"{idx}. {booking['datetime']} - {booking['direction']} - {booking['trainer']}\n"
            cancel_text += "\nНапиши номер записи, которую хочешь отменить (1, 2, 3...):"
            send_message(user_id, cancel_text)
    
    elif message == 'расписание':
        if os.path.exists(PHOTO_SCHEDULE):
            send_photo(user_id, PHOTO_SCHEDULE, "📅 Расписание занятий:")
        else:
            send_message(user_id, "📅 Расписание занятий временно недоступно", keyboard=get_main_keyboard())
    
    elif message == 'прайс':
        if os.path.exists(PHOTO_PRICES):
            send_photo(user_id, PHOTO_PRICES, "💰 Наш прайс:")
        else:
            text = "💰 Прайс на занятия:\n\nРазовое занятие — 700 руб.\nАбонемент на 4 занятия — 2500 руб.\nАбонемент на 8 занятий — 4500 руб."
            send_message(user_id, text, keyboard=get_main_keyboard())
    
    elif message == 'контакты':
        text = "📍 г. Королёв, Октябрьский бул, д. 26\n🌐 Сайт: https://taplink.cc/ka24"
        if os.path.exists(PHOTO_CONTACTS):
            send_photo(user_id, PHOTO_CONTACTS, text)
        else:
            send_message(user_id, text, keyboard=get_main_keyboard())
    
    elif message == 'отзыв':
        user_states[user_id] = {'state': 'WAITING_FEEDBACK_RATING', 'data': {}}
        send_message(user_id, "Оцени занятие от 1 до 5:")
    
    elif message == 'админ':
        user_states[user_id] = {'state': 'WAITING_ADMIN_QUESTION', 'data': {}}
        send_message(user_id, "Напиши свой вопрос, и я передам его администратору:", keyboard=get_back_keyboard())
    
    elif message in ['◀️ Назад', '◀️ Назад в меню']:
        user_states[user_id] = {'state': 'START', 'data': {}}
        send_message(user_id, "Выбери действие:", keyboard=get_main_keyboard())
    
    else:
        welcome_text = "✨ Привет! Я бот танцевальной студии КА24 ✨\n\nВыбери действие:"
        send_message(user_id, welcome_text, keyboard=get_main_keyboard())

# ===== ЗАПУСК БОТА =====
vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

print("✅ Бот запущен и слушает сообщения...")
print("📌 Команды: Записаться, Отменить запись, Расписание, Прайс, Контакты, Отзыв, Админ")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
        user_id = event.message.from_id
        message = event.message.text.strip()
        
        print(f"📩 {user_id}: {message}")
        
        if user_id not in user_states:
            user_states[user_id] = {'state': 'START', 'data': {}}
        
        state = user_states[user_id]['state']
        
        # Обработка навигации назад
        if message in ["◀️ Назад", "◀️ Назад в меню"]:
            user_states[user_id] = {'state': 'START', 'data': {}}
            send_message(user_id, "Выбери действие:", keyboard=get_main_keyboard())
            continue
        
        # ===== ОТМЕНА ЗАПИСИ - ВЫБОР ИЗ СПИСКА =====
        if state == 'CANCEL_SELECT':
            try:
                choice = int(message) - 1
                bookings = user_states[user_id]['data'].get('cancel_bookings', [])
                if 0 <= choice < len(bookings):
                    booking = bookings[choice]
                    user_states[user_id]['data']['cancel_row_id'] = booking['row_id']
                    user_states[user_id]['data']['cancel_booking'] = booking
                    user_states[user_id]['state'] = 'CANCEL_CONFIRM'
                    
                    booking_info = f"📅 {booking['datetime']}\n💃 {booking['direction']}\n👨‍🏫 {booking['trainer']}"
                    send_message(user_id, f"Отменить эту запись?\n\n{booking_info}", 
                               keyboard=get_cancel_keyboard())
                else:
                    send_message(user_id, "❌ Неверный номер. Пожалуйста, выбери номер из списка.")
            except ValueError:
                send_message(user_id, "❌ Пожалуйста, введи номер записи цифрой.")
        
        # ===== ОТМЕНА ЗАПИСИ - ПОДТВЕРЖДЕНИЕ =====
        elif state == 'CANCEL_CONFIRM':
            if message in ["✅ Да, отменить", "да", "yes"]:
                row_id = user_states[user_id]['data'].get('cancel_row_id')
                if row_id and cancel_booking(row_id):
                    send_message(user_id, "✅ Запись успешно отменена!\n\nЕсли хочешь записаться снова, нажми 'Записаться'", 
                               keyboard=get_main_keyboard())
                    # Уведомляем администратора
                    try:
                        booking = user_states[user_id]['data'].get('cancel_booking', {})
                        admin_msg = f"❌ ОТМЕНА ЗАПИСИ!\n\n👤 {booking.get('name', '')}\n💃 {booking.get('direction', '')}\n👨‍🏫 {booking.get('trainer', '')}\n📅 {booking.get('datetime', '')}"
                        vk.messages.send(user_id=ADMIN_VK_ID, message=admin_msg, random_id=random.randint(1, 10**9))
                        print(f"✅ Уведомление об отмене отправлено администратору")
                    except Exception as e:
                        print(f"❌ Ошибка отправки админу: {e}")
                else:
                    send_message(user_id, "❌ Не удалось отменить запись. Пожалуйста, свяжитесь с администратором.", 
                               keyboard=get_main_keyboard())
                user_states[user_id] = {'state': 'START', 'data': {}}
            elif message in ["❌ Нет, оставить", "нет", "no"]:
                send_message(user_id, "✅ Отмена записи отменена. Запись остаётся активной.", 
                           keyboard=get_main_keyboard())
                user_states[user_id] = {'state': 'START', 'data': {}}
            else:
                send_message(user_id, "Пожалуйста, выбери действие из кнопок:", 
                           keyboard=get_cancel_keyboard())
        
        # ===== ОСНОВНЫЕ СОСТОЯНИЯ (ЗАПИСЬ) =====
        elif state == 'START':
            handle_start(user_id, message.lower())
        
        elif state == 'WAITING_CATEGORY':
            if message == "🧒 Детские направления":
                user_states[user_id]['data']['category'] = 'kids'
                user_states[user_id]['data']['list_type'] = 'first'
                user_states[user_id]['state'] = 'WAITING_DIRECTION'
                send_message(user_id, "Выбери детское направление:", 
                           keyboard=get_directions_keyboard(KIDS_DIRECTIONS_1, True, 'kids'))
            elif message == "👩 Взрослые направления":
                user_states[user_id]['data']['category'] = 'adults'
                user_states[user_id]['data']['list_type'] = 'first'
                user_states[user_id]['state'] = 'WAITING_DIRECTION'
                send_message(user_id, "Выбери взрослое направление:", 
                           keyboard=get_directions_keyboard(ADULTS_DIRECTIONS_1, True, 'adults'))
            else:
                send_message(user_id, "Пожалуйста, выбери категорию из кнопок:", 
                           keyboard=get_category_keyboard())
        
        elif state == 'WAITING_DIRECTION':
            category = user_states[user_id]['data'].get('category', 'adults')
            list_type = user_states[user_id]['data'].get('list_type', 'first')
            
            if category == 'kids':
                if list_type == 'first':
                    current_directions = KIDS_DIRECTIONS_1
                    other_button = "🔄 Другие детские"
                else:
                    current_directions = KIDS_DIRECTIONS_2
                    other_button = "🔄 Первые детские"
            else:
                if list_type == 'first':
                    current_directions = ADULTS_DIRECTIONS_1
                    other_button = "🔄 Другие взрослые"
                else:
                    current_directions = ADULTS_DIRECTIONS_2
                    other_button = "🔄 Первые взрослые"
            
            if message == other_button:
                user_states[user_id]['data']['list_type'] = 'second' if list_type == 'first' else 'first'
                if category == 'kids':
                    new_list = KIDS_DIRECTIONS_2 if list_type == 'first' else KIDS_DIRECTIONS_1
                else:
                    new_list = ADULTS_DIRECTIONS_2 if list_type == 'first' else ADULTS_DIRECTIONS_1
                send_message(user_id, f"Вот другие направления:", 
                           keyboard=get_directions_keyboard(new_list, list_type == 'first', category))
            elif message == "🔄 Другая категория":
                user_states[user_id]['state'] = 'WAITING_CATEGORY'
                send_message(user_id, "Выбери категорию:", keyboard=get_category_keyboard())
            elif message in current_directions:
                user_states[user_id]['data']['direction'] = message
                user_states[user_id]['state'] = 'WAITING_TRAINER'
                send_message(user_id, f"Выбрано: {message}\n\nТеперь выбери тренера:", 
                           keyboard=get_trainers_keyboard(message))
            else:
                send_message(user_id, "Пожалуйста, выбери направление из кнопок:", 
                           keyboard=get_directions_keyboard(current_directions, list_type == 'first', category))
        
        elif state == 'WAITING_TRAINER':
            direction = user_states[user_id]['data']['direction']
            trainers = list(SCHEDULE.get(direction, {}).keys())
            
            if message == "🔄 Выбрать другое направление":
                category = user_states[user_id]['data'].get('category', 'adults')
                list_type = user_states[user_id]['data'].get('list_type', 'first')
                if category == 'kids':
                    current_directions = KIDS_DIRECTIONS_1 if list_type == 'first' else KIDS_DIRECTIONS_2
                else:
                    current_directions = ADULTS_DIRECTIONS_1 if list_type == 'first' else ADULTS_DIRECTIONS_2
                user_states[user_id]['state'] = 'WAITING_DIRECTION'
                send_message(user_id, "Выбери направление:", 
                           keyboard=get_directions_keyboard(current_directions, list_type == 'first', category))
            elif message in trainers:
                user_states[user_id]['data']['trainer'] = message
                user_states[user_id]['state'] = 'WAITING_SCHEDULE'
                send_message(user_id, f"Выбрана тренер: {message}\n\nДоступные занятия:", 
                           keyboard=get_schedule_keyboard(direction, message))
            else:
                send_message(user_id, "Пожалуйста, выбери тренера из кнопок:", 
                           keyboard=get_trainers_keyboard(direction))
        
        elif state == 'WAITING_SCHEDULE':
            direction = user_states[user_id]['data']['direction']
            trainer = user_states[user_id]['data']['trainer']
            
            if message == "✏️ Выбрать другое время":
                user_states[user_id]['state'] = 'WAITING_CUSTOM_DATETIME'
                send_message(user_id, "Укажи желаемую дату и время в формате: ДД.ММ.ГГГГ ЧЧ:ММ\n\nПример: 25.05.2026 19:00")
            elif message == "🔄 Выбрать другого тренера":
                user_states[user_id]['state'] = 'WAITING_TRAINER'
                send_message(user_id, f"Выбери другого тренера для направления {direction}:", 
                           keyboard=get_trainers_keyboard(direction))
            elif message != "◀️ Назад в меню":
                user_states[user_id]['data']['datetime'] = message
                user_states[user_id]['state'] = 'WAITING_NAME'
                send_message(user_id, "Отлично! Теперь скажи, как тебя зовут?")
            else:
                send_message(user_id, "Пожалуйста, выбери время из предложенных вариантов:", 
                           keyboard=get_schedule_keyboard(direction, trainer))
        
        elif state == 'WAITING_CUSTOM_DATETIME':
            user_states[user_id]['data']['datetime'] = message
            user_states[user_id]['state'] = 'WAITING_NAME'
            send_message(user_id, "Отлично! Теперь скажи, как тебя зовут?")
        
        elif state == 'WAITING_NAME':
            if len(message) >= 2:
                user_states[user_id]['data']['name'] = message
                user_states[user_id]['state'] = 'WAITING_PHONE'
                send_message(user_id, "Укажи номер телефона для связи\n\nФормат: 79991234567 или 89991234567")
            else:
                send_message(user_id, "Пожалуйста, введите имя (минимум 2 буквы):")
        
        elif state == 'WAITING_PHONE':
            is_valid, clean_phone = validate_phone(message)
            if is_valid:
                user_states[user_id]['data']['phone'] = clean_phone
                user_states[user_id]['state'] = 'CONFIRMATION'
                data = user_states[user_id]['data']
                confirm_text = f"📝 ПРОВЕРЬ ЗАПИСЬ:\n\n💃 Направление: {data['direction']}\n👨‍🏫 Тренер: {data['trainer']}\n📅 Дата/время: {data['datetime']}\n👤 Имя: {data['name']}\n📞 Телефон: +{data['phone']}\n\nВсё верно?"
                send_message(user_id, confirm_text, keyboard=get_confirmation_keyboard())
            else:
                send_message(user_id, "❌ Неверный формат телефона.\n\nВведите номер в формате:\n79991234567 или 89123456789")
        
        elif state == 'CONFIRMATION':
            if message in ["✅ Да, все верно", "да", "yes", "+", "конечно", "подтверждаю"]:
                data = user_states[user_id]['data']
                try:
                    sheet = get_sheet("Заявки")
                    row = [
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        data['name'],
                        data['phone'],
                        data['direction'],
                        data['trainer'],
                        data['datetime'],
                        "новая",
                        user_id
                    ]
                    sheet.append_row(row)
                    send_message(user_id, "✅ Спасибо! Заявка отправлена администратору. Мы свяжемся с тобой в ближайшее время.", 
                               keyboard=get_main_keyboard())
                    
                    try:
                        admin_msg = f"📝 Новая заявка!\n\n👤 {data['name']}\n📞 +{data['phone']}\n💃 {data['direction']}\n👨‍🏫 {data['trainer']}\n📅 {data['datetime']}"
                        vk.messages.send(user_id=ADMIN_VK_ID, message=admin_msg, random_id=random.randint(1, 10**9))
                        print(f"✅ Уведомление отправлено администратору")
                    except Exception as e:
                        print(f"❌ Ошибка отправки админу: {e}")
                    
                    user_states[user_id] = {'state': 'START', 'data': {}}
                except Exception as e:
                    print(f"❌ Ошибка сохранения в Google: {e}")
                    send_message(user_id, f"❌ Ошибка сохранения. Пожалуйста, попробуй позже.", 
                               keyboard=get_main_keyboard())
            elif message in ["❌ Нет, нужно исправить", "нет", "no", "-", "исправить"]:
                user_states[user_id] = {'state': 'START', 'data': {}}
                send_message(user_id, "Давай начнём запись заново. Выбери категорию:", 
                           keyboard=get_category_keyboard())
            else:
                send_message(user_id, "Пожалуйста, подтверди или отмени запись, используя кнопки:", 
                           keyboard=get_confirmation_keyboard())
        
        elif state == 'WAITING_FEEDBACK_RATING':
            if message in ['1', '2', '3', '4', '5']:
                user_states[user_id]['data']['rating'] = message
                user_states[user_id]['state'] = 'WAITING_FEEDBACK_COMMENT'
                send_message(user_id, "Напиши, что понравилось или что можно улучшить:")
            else:
                send_message(user_id, "Пожалуйста, поставь оценку от 1 до 5:")
        
        elif state == 'WAITING_FEEDBACK_COMMENT':
            try:
                sheet = get_sheet("Отзывы")
                row = [
                    datetime.now().strftime("%Y-%m-%d"),
                    user_states[user_id]['data'].get('name', 'Аноним'),
                    user_states[user_id]['data']['rating'],
                    message
                ]
                sheet.append_row(row)
                send_message(user_id, "🙏 Спасибо за обратную связь! Это помогает нам становиться лучше.", 
                           keyboard=get_main_keyboard())
            except Exception as e:
                print(f"❌ Ошибка сохранения отзыва: {e}")
                send_message(user_id, "🙏 Спасибо за обратную связь!", keyboard=get_main_keyboard())
            user_states[user_id] = {'state': 'START', 'data': {}}
        
        elif state == 'WAITING_ADMIN_QUESTION':
            try:
                admin_msg = f"❓ ВОПРОС ОТ ПОЛЬЗОВАТЕЛЯ:\n\nID: {user_id}\n\nСообщение: {message}"
                vk.messages.send(user_id=ADMIN_VK_ID, message=admin_msg, random_id=random.randint(1, 10**9))
                print(f"✅ Вопрос переслан администратору")
                send_message(user_id, "✅ Сообщение отправлено администратору. Ответ придёт в ближайшее время.", 
                           keyboard=get_main_keyboard())
            except Exception as e:
                print(f"❌ Ошибка отправки админу: {e}")
                send_message(user_id, "❌ Не удалось отправить сообщение. Пожалуйста, свяжитесь с администратором по телефону.", 
                           keyboard=get_main_keyboard())
            user_states[user_id] = {'state': 'START', 'data': {}}
