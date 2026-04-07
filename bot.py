import telebot
from telebot import types
from datetime import datetime
from groq import Groq
import sqlite3
import requests
import os

# ================== ENVIRONMENT VARIABLES ==================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    print("❌ Token belum di-set!")
    exit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

# ================== DATABASE (tetap sama) ==================
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
    ''', (user.id, user.username, user.full_name, None, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
    markup.add('ℹ️ Info', '📸 Kirim Foto', '🕒 Waktu', '👋 Halo', '🤖 AI Chat', '👤 Profile', '🌤️ Cuaca')
    return markup

# ================== FUNGSI CUACA ==================
def get_weather(city="Medan"):
    try:
        # Open-Meteo API (gratis, no key)
        url = f"https://api.open-meteo.com/v1/forecast?latitude=3.58&longitude=98.67&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&timezone=Asia/Jakarta&forecast_days=2"
        
        if city.lower() != "medan":
            # Untuk kota lain, kita pakai koordinat sederhana (bisa dikembangkan)
            bot.send_message(chat_id, "Saat ini hanya support Medan dengan akurat. Kota lain akan ditambahkan nanti.")
            city = "Medan"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data['current']
        temp = current['temperature_2m']
        humidity = current['relative_humidity_2m']
        wind = current['wind_speed_10m']
        
        weather_code = current['weather_code']
        condition = {
            0: "Cerah ☀️",
            1: "Cerah berawan 🌤️",
            2: "Berawan 🌥️",
            3: "Mendung ☁️",
            45: "Kabut 🌫️",
            51: "Gerimis ringan 🌧️",
            61: "Hujan sedang 🌧️",
            80: "Hujan deras 🌧️",
        }.get(weather_code, "Cuaca tidak diketahui")
        
        teks = f"🌤️ **Cuaca di Medan sekarang**\n\n" \
               f"🌡️ Suhu: {temp}°C\n" \
               f"💧 Kelembapan: {humidity}%\n" \
               f"🌬️ Angin: {wind} km/jam\n" \
               f"☁️ Kondisi: {condition}\n\n" \
               f"Data dari Open-Meteo"
        
        return teks
    except:
        return "Maaf, gagal mengambil data cuaca. Coba lagi nanti."

# ================== HANDLER ==================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    save_user(message.from_user)
    bot.reply_to(message, f"Halo {message.from_user.first_name}! 👋\nBot Adrian Medan sudah update dengan fitur Cuaca.", reply_markup=main_menu())

@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_data = get_user(message.from_user.id)
    if user_data:
        _, username, full_name, custom_name, join_date = user_data
        nama = custom_name if custom_name else full_name
        teks = f"👤 **Profile Kamu**\n\nNama: {nama}\nUsername: @{username if username else 'Tidak ada'}\nBergabung: {join_date}"
        bot.reply_to(message, teks, parse_mode="Markdown")
    else:
        bot.reply_to(message, "Data belum tersimpan.")

@bot.message_handler(commands=['setnama'])
def set_custom_name(message):
    bot.reply_to(message, "Masukkan nama panggilan baru:")
    bot.register_next_step_handler(message, process_custom_name)

def process_custom_name(message):
    custom_name = message.text.strip()
    update_custom_name(message.from_user.id, custom_name)
    bot.reply_to(message, f"Nama panggilan diubah menjadi: **{custom_name}** ✅", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text.strip()

    save_user(message.from_user)

    if text == 'ℹ️ Info':
        bot.reply_to(message, "🤖 Bot Adrian Medan Versi E (Fitur 1: Cuaca ditambahkan)")
        return
    elif text == '📸 Kirim Foto':
        try:
            with open('gambar.jpg', 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="Foto dari Adrian")
        except:
            bot.reply_to(message, "Foto belum ada.")
        return
    elif text == '🕒 Waktu':
        sekarang = datetime.now().strftime("%H:%M:%S | %d %B %Y")
        bot.reply_to(message, f"🕒 Waktu sekarang: {sekarang} WIB")
        return
    elif text == '👋 Halo':
        bot.reply_to(message, "Halo juga! Apa kabar?")
        return
    elif text == '🤖 AI Chat':
        bot.reply_to(message, "🤖 Groq AI aktif! Ketik apa saja...")
        return
    elif text == '👤 Profile':
        show_profile(message)
        return
    elif text == '🌤️ Cuaca':
        cuaca_text = get_weather("Medan")
        bot.reply_to(message, cuaca_text, parse_mode="Markdown")
        return

    # Groq AI Chat (tetap sama)
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
    except:
        bot.reply_to(message, "Maaf, AI lagi sibuk.")

print("✅ Bot dengan Fitur 1 (Cuaca) sedang berjalan...")
bot.polling(none_stop=True)
