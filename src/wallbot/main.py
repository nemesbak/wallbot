import logging
import threading

from src.wallbot.telegram.handlers import TelegramHandlers
from .database.db_helper import DBHelper
from .telegram.bot import create_bot, start_polling
from .utils.logger import setup_logger
from .utils.version import read_version
from .wallapop.monitor import WallapopMonitor


def _notify_startup(bot, db):
    chat_ids = db.get_all_active_chat_ids()
    if not chat_ids:
        return
    for chat_id in chat_ids:
        try:
            searches = db.get_chat_searches(chat_id)
            n = len([s for s in searches if s.active == 1])
            bot.send_message(
                chat_id,
                f"✅ <b>WallBot reiniciado</b>\n"
                f"Monitorizando <b>{n}</b> alerta{'s' if n != 1 else ''}.",
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Error notificando reinicio a {chat_id}: {e}")


def main():
    setup_logger()
    logging.info("JanJanJan starting...")

    db = DBHelper()
    db.setup(read_version())

    bot = create_bot()

    TelegramHandlers(bot, db)

    monitor = WallapopMonitor(db, bot)
    threading.Thread(target=monitor.start, daemon=True).start()

    _notify_startup(bot, db)

    start_polling(bot)


if __name__ == '__main__':
    main()
