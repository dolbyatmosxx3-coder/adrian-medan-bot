import telebot
from telebot import types
from datetime import datetime
from groq import Groq
import sqlite3
import os

# ================== AMBIL DARI ENVIRONMENT VARIABLES ==================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    print("❌ TELEGRAM_TOKEN atau GROQ_API_KEY belum di-set di Railway/Render!")
    exit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

# ================== DATABASE SQLITE ==================
DB_NAME = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            custom_name TEXT,
            join_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user(user):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (telegram_id, username, full_name, custom_name, join_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        user.id,
        user.username,
        user.full_name,
        None,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

def get_user(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_custom_name(telegram_id, custom_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET custom_name = ? WHERE telegram_id = ?", (custom_name, telegram_id))
    conn.commit()
    conn.close()

init_db()

user_history = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('ℹ️ Info', '📸 Kirim Foto', '🕒 Waktu', '👋 Halo', '🤖 AI Chat', '👤 Profile')
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    save_user(message.from_user)
    teks = f"Halo {message.from_user.first_name}! 👋\nBot Adrian Medan sudah online 24 jam via Railway.\nKetik /profile untuk melihat data kamu."
    bot.reply_to(message, teks, reply_markup=main_menu())

@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_data = get_user(message.from_user.id)
    if user_data:
        telegram_id, username, full_name, custom_name, join_date = user_data
        nama = custom_name if custom_name else full_name
        teks = f"👤 **Profile Kamu**\n\nNama: {nama}\nUsername: @{username if username else 'Tidak ada'}\nID: {telegram_id}\nBergabung: {join_date}"
        bot.reply_to(message, teks, parse_mode="Markdown")
    else:
        bot.reply_to(message, "Data kamu belum tersimpan.")

@bot.message_handler(commands=['setnama'])
def set_custom_name(message):
    bot.reply_to(message, "Masukkan nama panggilan baru kamu:")
    bot.register_next_step_handler(message, process_custom_name)

def process_custom_name(message):
    custom_name = message.text.strip()
    update_custom_name(message.from_user.id, custom_name)
    bot.reply_to(message, f"Nama panggilan berhasil diubah menjadi: **{custom_name}** ✅", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text.strip()

    save_user(message.from_user)

    if text == 'ℹ️ Info':
        bot.reply_to(message, "🤖 Bot Adrian Medan Versi D (Deployed on Railway)")
        return
    elif text == '📸 Kirim Foto':
        try:
            with open('gambar.jpg', 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="Foto dari Adrian")
        except:
            bot.reply_to(message, "Maaf, file gambar.jpg belum ada.")
        return
    elif text == '🕒 Waktu':
        sekarang = datetime.now().strftime("%H:%M:%S | %d %B %Y")
        bot.reply_to(message, f"🕒 Waktu sekarang: {sekarang} WIB")
        return
    elif text == '👋 Halo':
        bot.reply_to(message, "Halo juga bro! Apa kabar?")
        return
    elif text == '🤖 AI Chat':
        bot.reply_to(message, "🤖 Mode AI Groq aktif! Ketik apa saja...")
        return
    elif text == '👤 Profile':
        show_profile(message)
        return

    # AI Groq
    bot.reply_to(message, "🤖 Sedang mikir...")
    try:
        if user_id not in user_history:
            user_history[user_id] = [
                {"role": "system", "content": "Kamu adalah AdrianBot dari Medan. Jawab santai, ramah, pakai bahasa Indonesia sehari-hari."}
            ]

        user_history[user_id].append({"role": "user", "content": text})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_history[user_id],
            temperature=0.7,
            max_tokens=800
        )

        ai_reply = completion.choices[0].message.content
        user_history[user_id].append({"role": "assistant", "content": ai_reply})
        bot.reply_to(message, ai_reply)

    except Exception as e:
        bot.reply_to(message, "Maaf, AI lagi sibuk. Coba lagi ya.")

print("✅ Bot Versi D (Deploy Ready) sedang berjalan...")
bot.polling(none_stop=True)