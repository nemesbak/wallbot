import logging
from urllib.parse import urlencode

import requests

from src.wallbot.config.settings import WALLAPOP_API_URL
from src.wallbot.database.models import ChatSearch

try:
    from fake_useragent import UserAgent
    _ua = UserAgent()
except Exception:
    _ua = None
    logging.warning("fake_useragent no disponible, usando header por defecto")


class WallapopClient:
    def __init__(self):
        self.base_url = WALLAPOP_API_URL

    def _get_headers(self):
        if _ua:
            return {'User-Agent': _ua.random, 'x-deviceos': '0'}
        return {'x-deviceos': '0'}

    def search_items(self, search: ChatSearch, time_filter: str = 'today'):
        url = self._build_search_url(search, time_filter=time_filter)
        logging.debug(f"API Wallapop ->: {url}")
        try:
            response = requests.get(url=url, headers=self._get_headers())
            response.raise_for_status()
            logging.debug(f"API Wallapop <-: {response.json()}")
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error en API Wallapop: {e}")
            return None

    def _build_search_url(self, search, time_filter: str = 'today'):
        params = {
            'source': 'search_box',
            'keywords': search.kws,
        }
        if time_filter:
            params['time_filter'] = time_filter
        if search.cat_ids:
            params['category_ids'] = search.cat_ids
        if search.min_price:
            params['min_sale_price'] = search.min_price
        if search.max_price:
            params['max_sale_price'] = search.max_price
        if search.dist:
            params['dist'] = search.dist
        if search.orde:
            params['order_by'] = search.orde
        return f"{self.base_url}?{urlencode(params)}"
