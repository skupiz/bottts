import telebot
import sqlite3
import json
import os
import time

# Токен из переменных окружения (так безопаснее)
TOKEN = os.environ.get('BOT_TOKEN', '8278343451:AAEzDlT0BrxYdPhHhcDRSzGNFSjQid_4AKA')
bot = telebot.TeleBot(TOKEN)

# Подключение к базе данных
conn = sqlite3.connect('duties.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы
cursor.execute('''
CREATE TABLE IF NOT EXISTS duties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT UNIQUE NOT NULL,
    queue TEXT NOT NULL,
    current_index INTEGER NOT NULL
)
''')
conn.commit()

PEOPLE = ['Глеб', 'Егор', 'Денис', 'Кирилл']

def init_task(task):
    cursor.execute("SELECT * FROM duties WHERE task = ?", (task,))
    if not cursor.fetchone():
        queue_json = json.dumps(PEOPLE, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO duties (task, queue, current_index) VALUES (?, ?, 0)",
            (task, queue_json)
        )
        conn.commit()

init_task('мусор')
init_task('дежурный')

def get_current(task):
    cursor.execute("SELECT queue, current_index FROM duties WHERE task = ?", (task,))
    row = cursor.fetchone()
    queue = json.loads(row[0])
    current_index = row[1]
    return queue[current_index]

def next_person(task):
    cursor.execute("SELECT queue, current_index FROM duties WHERE task = ?", (task,))
    row = cursor.fetchone()
    queue = json.loads(row[0])
    current_index = row[1]
    next_index = (current_index + 1) % len(queue)
    cursor.execute(
        "UPDATE duties SET current_index = ? WHERE task = ?",
        (next_index, task)
    )
    conn.commit()
    return queue[next_index]

def get_queue(task):
    cursor.execute("SELECT queue FROM duties WHERE task = ?", (task,))
    row = cursor.fetchone()
    return json.loads(row[0])

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "👋 Привет! Я бот для распределения обязанностей в комнате.\n\n"
        "📋 Доступные команды:\n"
        "/trash – отметить, что мусор вынесен\n"
        "/clean – отметить, что уборка сделана\n"
        "/info – показать текущих ответственных\n"
        "/queue – показать полный список очередей\n"
        "/list – то же, что и /queue"
    )

@bot.message_handler(commands=['trash'])
def trash_done(message):
    current = get_current('мусор')
    next_person_var = next_person('мусор')
    bot.send_message(message.chat.id, 
        f"🗑️ Мусор вынес {current}!\n"
        f"👉 Теперь очередь выносить мусор у {next_person_var}"
    )

@bot.message_handler(commands=['clean'])
def clean_done(message):
    current = get_current('дежурный')
    next_person_var = next_person('дежурный')
    bot.send_message(message.chat.id, 
        f"🧹 Дежурство выполнил {current}!\n"
        f"👉 Теперь дежурит {next_person_var}"
    )

@bot.message_handler(commands=['info'])
def show_info(message):
    trash_current = get_current('мусор')
    clean_current = get_current('дежурный')
    
    trash_queue = get_queue('мусор')
    clean_queue = get_queue('дежурный')
    
    trash_index = trash_queue.index(trash_current)
    next_trash = trash_queue[(trash_index + 1) % len(trash_queue)]
    
    clean_index = clean_queue.index(clean_current)
    next_clean = clean_queue[(clean_index + 1) % len(clean_queue)]
    
    bot.send_message(message.chat.id,
        f"📊 Текущая информация:\n\n"
        f"🗑️ **Вынос мусора:**\n"
        f"   Сейчас: {trash_current}\n"
        f"   Следующий: {next_trash}\n\n"
        f"🧹 **Дежурный по комнате:**\n"
        f"   Сейчас: {clean_current}\n"
        f"   Следующий: {next_clean}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['queue', 'list'])
def show_queue(message):
    trash_queue = get_queue('мусор')
    clean_queue = get_queue('дежурный')
    trash_current = get_current('мусор')
    clean_current = get_current('дежурный')
    
    trash_text = ""
    for person in trash_queue:
        if person == trash_current:
            trash_text += f"👉 **{person}** (сейчас) → "
        else:
            trash_text += f"{person} → "
    trash_text = trash_text[:-3]
    
    clean_text = ""
    for person in clean_queue:
        if person == clean_current:
            clean_text += f"👉 **{person}** (сейчас) → "
        else:
            clean_text += f"{person} → "
    clean_text = clean_text[:-3]
    
    bot.send_message(message.chat.id,
        f"📋 **Полный список очередей:**\n\n"
        f"🗑️ **Вынос мусора:**\n{trash_text}\n\n"
        f"🧹 **Дежурный по комнате:**\n{clean_text}\n\n"
        f"🔄 Очередь замыкается",
        parse_mode='Markdown'
    )

# Запуск с автоматическим перезапуском при ошибках
if __name__ == "__main__":
    print("✅ Бот запущен на Railway!")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, interval=1)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)