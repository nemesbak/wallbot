import locale
import logging
import time
from decimal import Decimal
from re import sub
from typing import List

from src.wallbot.config.constants import SEARCH_INTERVAL
from src.wallbot.database.models import ChatSearch
from src.wallbot.telegram.notifications import notel
from src.wallbot.wallapop.api_client import WallapopClient

_ITEM_RETENTION_HOURS = 7 * 24  # 7 días


class WallapopMonitor:
    def __init__(self, db, bot):
        self.db = db
        self.bot = bot
        self.client = WallapopClient()
        self.is_running = False

    def start(self):
        self.is_running = True
        logging.info("Iniciando monitoreo de Wallapop...")

        while self.is_running:
            try:
                self.db.delete_items(_ITEM_RETENTION_HOURS)
                self._monitor_cycle()
                time.sleep(SEARCH_INTERVAL)
            except KeyboardInterrupt:
                logging.info("Deteniendo monitoreo...")
                self.stop()
            except Exception as e:
                logging.error(f"Error en ciclo de monitoreo: {e}")
                time.sleep(SEARCH_INTERVAL)

    def stop(self):
        self.is_running = False
        logging.info("Monitoreo detenido")

    def _monitor_cycle(self):
        searches: List[ChatSearch] = self.db.get_chats_searches()
        for search in searches:
            try:
                response = self.client.search_items(search)
                if response:
                    self._handle_response(search, response)
            except Exception as e:
                logging.error(f"Error procesando búsqueda para chat `{search.chat_id}`: {e}")

    def _handle_response(self, search, response):
        try:
            items = response['data']['section']['payload']['items']
            for item in items:
                self._process_item(item, search)
        except (KeyError, ValueError) as e:
            logging.error(f"Error procesando respuesta de API: {e}")

    def _process_item(self, item, search):
        item_id       = item['id']
        item_price    = item['price']['amount']
        item_title    = item['title']
        item_user     = item['user_id']
        item_web_slug = item['web_slug']
        item_desc     = item.get('description', '') or ''
        image_url = None
        try:
            image_url = item['images'][0]['urls']['medium']
        except (KeyError, IndexError):
            pass

        logging.info('Encontrado: id=%s, price=%s, title=%s', item_id,
                     locale.currency(item_price, grouping=True), item_title)

        existing_item = self.db.search_item(item_id, search.chat_id)
        if existing_item is None:
            self._process_new_item(item_id, search.chat_id, item_title, item_price,
                                   item_web_slug, item_user, image_url, item_desc)
        else:
            self._process_price_update(existing_item, item_id, item_price,
                                       item_title, item_web_slug, search, image_url, item_desc)

    def _process_new_item(self, item_id, chat_id, title, price, web_slug, user_id, image_url, description=''):
        self.db.add_item(item_id, chat_id, title, price, web_slug, user_id)
        notel(self.bot, chat_id, price, title, web_slug, image_url=image_url, description=description)
        logging.info('New: id=%s, price=%s, title=%s', item_id,
                     locale.currency(price, grouping=True), title)

    def _process_price_update(self, existing_item, item_id, new_price, title, web_slug, search, image_url, description=''):
        new_price_decimal = Decimal(sub(r'[^\d.]', '', str(new_price)))
        old_price_decimal = Decimal(sub(r'[^\d.]', '', existing_item.price))

        if new_price_decimal >= old_price_decimal:
            return

        reduction_pct = int((1 - new_price_decimal / old_price_decimal) * 100)

        if search.min_drop_pct and reduction_pct < int(search.min_drop_pct):
            logging.info("Bajada del %d%% ignorada para '%s' (mínimo configurado: %s%%)",
                         reduction_pct, title, search.min_drop_pct)
            return

        price_history = locale.currency(float(old_price_decimal), grouping=True)
        if existing_item.observaciones:
            price_history += ' → ' + existing_item.observaciones

        self.db.update_item(item_id, search.chat_id, str(new_price), price_history)
        notel(self.bot, search.chat_id, new_price, title, web_slug,
              old_price=float(old_price_decimal),
              price_history=price_history,
              image_url=image_url,
              description=description)

        logging.info('Baja %d%%: id=%s, price=%s, title=%s', reduction_pct, item_id,
                     locale.currency(new_price, grouping=True), title)
