import time
import pytest
from src.wallbot.database.db_helper import DBHelper
from src.wallbot.database.models import ChatSearch


@pytest.fixture
def db():
    helper = DBHelper(":memory:")
    helper.setup()
    return helper


def cs(chat_id="c1", kws="ps5", **kwargs):
    return ChatSearch(chat_id=chat_id, kws=kws, active=1, **kwargs)


class TestAddSearch:

    def test_add_and_retrieve(self, db):
        db.add_search(cs(kws="ps5"))
        results = db.get_chat_searches("c1")
        assert len(results) == 1
        assert results[0].kws == "ps5"

    def test_stores_all_filters(self, db):
        db.add_search(cs(kws="ps5", min_price="200", max_price="350", dist="50", min_drop_pct=10))
        r = db.get_chat_searches("c1")[0]
        assert r.min_price == "200"
        assert r.max_price == "350"
        assert r.dist == "50"
        assert int(r.min_drop_pct) == 10

    def test_deleted_not_returned(self, db):
        db.add_search(cs(kws="ps5"))
        db.del_chat_search("c1", "ps5")
        assert db.get_chat_searches("c1") == []

    def test_paused_included(self, db):
        db.add_search(cs(kws="ps5"))
        db.pause_search("c1", "ps5")
        results = db.get_chat_searches("c1")
        assert len(results) == 1
        assert results[0].active == 2

    def test_isolated_by_chat(self, db):
        db.add_search(cs(chat_id="c1", kws="ps5"))
        db.add_search(cs(chat_id="c2", kws="xbox"))
        assert len(db.get_chat_searches("c1")) == 1
        assert db.get_chat_searches("c1")[0].kws == "ps5"


class TestDelChatSearch:

    def test_returns_true_on_success(self, db):
        db.add_search(cs(kws="ps5"))
        assert db.del_chat_search("c1", "ps5") is True

    def test_returns_false_when_not_found(self, db):
        assert db.del_chat_search("c1", "nonexistent") is False

    def test_returns_false_when_already_deleted(self, db):
        db.add_search(cs(kws="ps5"))
        db.del_chat_search("c1", "ps5")
        assert db.del_chat_search("c1", "ps5") is False


class TestUpdateItem:

    def test_update_only_affects_target_chat(self, db):
        db.add_item("item1", "chat_a", "PS5", "500", "slug", "u1")
        db.add_item("item1", "chat_b", "PS5", "500", "slug", "u1")
        db.update_item("item1", "chat_a", "400", "historial")
        assert db.search_item("item1", "chat_a").price == "400"
        assert db.search_item("item1", "chat_b").price == "500"

    def test_stores_observaciones(self, db):
        db.add_item("item1", "c1", "PS5", "500", "slug", "u1")
        db.update_item("item1", "c1", "400", "500,00 €")
        assert db.search_item("item1", "c1").observaciones == "500,00 €"


class TestPauseResume:

    def test_pause_sets_active_2(self, db):
        db.add_search(cs(kws="ps5"))
        db.pause_search("c1", "ps5")
        assert db.get_chat_searches("c1")[0].active == 2

    def test_resume_sets_active_1(self, db):
        db.add_search(cs(kws="ps5"))
        db.pause_search("c1", "ps5")
        db.resume_search("c1", "ps5")
        assert db.get_chat_searches("c1")[0].active == 1


class TestGetChatsSearches:

    def test_returns_only_active_for_monitor(self, db):
        db.add_search(cs(chat_id="c1", kws="ps5"))
        db.add_search(cs(chat_id="c2", kws="xbox"))
        db.add_search(cs(chat_id="c3", kws="switch"))
        db.del_chat_search("c3", "switch")
        results = db.get_chats_searches()
        chat_ids = {r.chat_id for r in results}
        assert "c1" in chat_ids
        assert "c2" in chat_ids
        assert "c3" not in chat_ids

    def test_paused_excluded_from_monitor_cycle(self, db):
        db.add_search(cs(chat_id="c1", kws="ps5"))
        db.pause_search("c1", "ps5")
        results = db.get_chats_searches()
        assert all(r.chat_id != "c1" for r in results)


class TestStats:

    def test_active_and_paused_counts(self, db):
        db.add_search(cs(kws="ps5"))
        db.add_search(cs(kws="xbox"))
        db.pause_search("c1", "xbox")
        stats = db.get_stats("c1")
        assert stats['active'] == 1
        assert stats['paused'] == 1

    def test_items_and_drops_counts(self, db):
        db.add_item("i1", "c1", "PS5", "500", "s1", "u1")
        db.add_item("i2", "c1", "Xbox", "400", "s2", "u1", observaciones="500")
        stats = db.get_stats("c1")
        assert stats['items_found'] == 2
        assert stats['price_drops'] == 1


class TestDeleteItems:

    def test_old_items_deleted(self, db):
        old_ts = int(time.time() * 1000) - (10 * 24 * 3600 * 1000)
        db.add_item("i1", "c1", "PS5", "500", "slug", "u1", publish_date=old_ts)
        db.delete_items(7 * 24)
        assert db.search_item("i1", "c1") is None

    def test_recent_items_kept(self, db):
        recent_ts = int(time.time() * 1000) - (3 * 24 * 3600 * 1000)
        db.add_item("i1", "c1", "PS5", "500", "slug", "u1", publish_date=recent_ts)
        db.delete_items(7 * 24)
        assert db.search_item("i1", "c1") is not None
