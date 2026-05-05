import pytest
from urllib.parse import urlparse, parse_qs
from src.wallbot.wallapop.api_client import WallapopClient
from src.wallbot.database.models import ChatSearch


@pytest.fixture
def client():
    return WallapopClient()


def search(**kwargs):
    defaults = dict(kws="ps5", min_price=None, max_price=None,
                    dist=None, cat_ids=None, orde=None, publish_date=None)
    defaults.update(kwargs)
    return ChatSearch(**defaults)


def params(url):
    return parse_qs(urlparse(url).query)


class TestBuildSearchUrl:

    def test_required_params_always_present(self, client):
        p = params(client._build_search_url(search()))
        assert p['keywords'] == ['ps5']
        assert p['source'] == ['search_box']
        assert p['time_filter'] == ['today']

    def test_keyword_with_spaces(self, client):
        p = params(client._build_search_url(search(kws="nintendo switch")))
        assert p['keywords'] == ['nintendo switch']

    def test_keyword_with_ampersand_encoded(self, client):
        p = params(client._build_search_url(search(kws="iphone & samsung")))
        assert p['keywords'] == ['iphone & samsung']

    def test_keyword_with_enie(self, client):
        p = params(client._build_search_url(search(kws="cañón")))
        assert p['keywords'] == ['cañón']

    def test_price_range_included(self, client):
        p = params(client._build_search_url(search(min_price="200", max_price="350")))
        assert p['min_sale_price'] == ['200']
        assert p['max_sale_price'] == ['350']

    def test_dist_included(self, client):
        p = params(client._build_search_url(search(dist="50")))
        assert p['dist'] == ['50']

    def test_order_included(self, client):
        p = params(client._build_search_url(search(orde="newest")))
        assert p['order_by'] == ['newest']

    def test_optional_params_absent_when_none(self, client):
        p = params(client._build_search_url(search()))
        assert 'min_sale_price' not in p
        assert 'max_sale_price' not in p
        assert 'dist' not in p
        assert 'category_ids' not in p
        assert 'order_by' not in p

    def test_all_optional_params_included(self, client):
        p = params(client._build_search_url(
            search(min_price="100", max_price="500", dist="30", cat_ids="200", orde="newest")
        ))
        assert 'min_sale_price' in p
        assert 'max_sale_price' in p
        assert 'dist' in p
        assert 'category_ids' in p
        assert 'order_by' in p
