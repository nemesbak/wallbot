import logging
import time

import telebot

from src.wallbot.config.settings import TOKEN


def create_bot():
    logging.info("Creating bot...")
    bot = telebot.TeleBot(TOKEN)
    _register_commands(bot)
    return bot


def _register_commands(bot):
    commands = [
        telebot.types.BotCommand('search',      'Buscar en Wallapop ahora'),
        telebot.types.BotCommand('add',         'Crear alerta de precio'),
        telebot.types.BotCommand('lis',         'Ver y gestionar alertas'),
        telebot.types.BotCommand('stats',       'Estadísticas'),
        telebot.types.BotCommand('del',         'Eliminar una alerta'),
        telebot.types.BotCommand('clear',       'Borrar todas las alertas'),
        telebot.types.BotCommand('help',        'Ayuda y referencia'),
    ]
    try:
        bot.set_my_commands(commands)
        logging.info("Comandos de bot registrados en Telegram.")
    except Exception as e:
        logging.warning(f"No se pudieron registrar comandos: {e}")


def start_polling(bot):
    delay = 1
    while True:
        try:
            logging.info("Conexión a Telegram.")
            bot.polling(none_stop=True, timeout=3000)
            delay = 1
        except Exception as e:
            logging.error(f"Error con Telegram, reintentando en {delay}s: {e}")
            time.sleep(delay)
            delay = min(delay * 2, 16)
