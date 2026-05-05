import pytest
from unittest.mock import MagicMock, patch
from src.wallbot.wallapop.monitor import WallapopMonitor
from src.wallbot.database.models import ChatSearch, Item


@pytest.fixture
def monitor():
    return WallapopMonitor(db=MagicMock(), bot=MagicMock())


def search(chat_id="c1", min_drop_pct=None):
    return ChatSearch(chat_id=chat_id, kws="ps5", min_drop_pct=min_drop_pct)


def item(price="500", obs=None):
    return Item("item1", "c1", "PS5", price, "ps5-slug", None, obs, None)


class TestProcessPriceUpdate:

    def test_price_increase_ignored(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel') as n:
            monitor._process_price_update(item("500"), "item1", 600, "PS5", "slug", search(), None)
            n.assert_not_called()
            monitor.db.update_item.assert_not_called()

    def test_same_price_ignored(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel') as n:
            monitor._process_price_update(item("500"), "item1", 500, "PS5", "slug", search(), None)
            n.assert_not_called()

    def test_drop_without_threshold_always_notifies(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel') as n, \
             patch('src.wallbot.wallapop.monitor.locale'):
            monitor._process_price_update(item("500"), "item1", 400, "PS5", "slug", search(min_drop_pct=None), None)
            n.assert_called_once()
            monitor.db.update_item.assert_called_once()

    def test_drop_above_threshold_notifies(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel') as n, \
             patch('src.wallbot.wallapop.monitor.locale'):
            # 20% de bajada, umbral 10% → notifica
            monitor._process_price_update(item("500"), "item1", 400, "PS5", "slug", search(min_drop_pct=10), None)
            n.assert_called_once()

    def test_drop_below_threshold_ignored(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel') as n, \
             patch('src.wallbot.wallapop.monitor.locale'):
            # 5% de bajada, umbral 20% → ignora
            monitor._process_price_update(item("500"), "item1", 475, "PS5", "slug", search(min_drop_pct=20), None)
            n.assert_not_called()
            monitor.db.update_item.assert_not_called()

    def test_drop_exactly_at_threshold_notifies(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel') as n, \
             patch('src.wallbot.wallapop.monitor.locale'):
            # 10% de bajada, umbral 10% → notifica (>=, no >)
            monitor._process_price_update(item("500"), "item1", 450, "PS5", "slug", search(min_drop_pct=10), None)
            n.assert_called_once()

    def test_update_item_called_with_correct_chat_id(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel'), \
             patch('src.wallbot.wallapop.monitor.locale'):
            monitor._process_price_update(item("500"), "item1", 400, "PS5", "slug", search(chat_id="chat99"), None)
            args = monitor.db.update_item.call_args[0]
            assert args[0] == "item1"
            assert args[1] == "chat99"

    def test_description_passed_to_notel(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel') as n, \
             patch('src.wallbot.wallapop.monitor.locale'):
            monitor._process_price_update(item("500"), "item1", 400, "PS5", "slug", search(), None, "desc aquí")
            kwargs = n.call_args[1]
            assert kwargs.get('description') == "desc aquí"

    def test_price_history_preserves_previous_observaciones(self, monitor):
        existing = item("500", obs="600,00 €")
        with patch('src.wallbot.wallapop.monitor.notel'), \
             patch('src.wallbot.wallapop.monitor.locale') as loc:
            loc.currency.return_value = "500,00 €"
            monitor._process_price_update(existing, "item1", 400, "PS5", "slug", search(), None)
            new_obs = monitor.db.update_item.call_args[0][3]
            assert "600,00 €" in new_obs


class TestProcessNewItem:

    def test_adds_to_db(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel'), \
             patch('src.wallbot.wallapop.monitor.locale'):
            monitor._process_new_item("item1", "c1", "PS5", 500, "ps5-slug", "u1", None)
            monitor.db.add_item.assert_called_once()

    def test_sends_notification(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel') as n, \
             patch('src.wallbot.wallapop.monitor.locale'):
            monitor._process_new_item("item1", "c1", "PS5", 500, "ps5-slug", "u1", None)
            n.assert_called_once()

    def test_description_passed_to_notel(self, monitor):
        with patch('src.wallbot.wallapop.monitor.notel') as n, \
             patch('src.wallbot.wallapop.monitor.locale'):
            monitor._process_new_item("item1", "c1", "PS5", 500, "slug", "u1", None, "descripción")
            kwargs = n.call_args[1]
            assert kwargs.get('description') == "descripción"
