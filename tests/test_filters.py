import pytest
from src.wallbot.telegram.handlers import TelegramHandlers

parse = TelegramHandlers._parse_filters
is_filter = TelegramHandlers._is_filter_token


class TestParseFilters:

    def test_price_range(self):
        f = parse("200-350")
        assert f['min_price'] == '200'
        assert f['max_price'] == '350'

    def test_max_price_only(self):
        f = parse("-350")
        assert f['min_price'] is None
        assert f['max_price'] == '350'

    def test_min_price_only(self):
        f = parse("200-")
        assert f['min_price'] == '200'
        assert f['max_price'] is None

    def test_drop_pct_without_dash(self):
        f = parse("10%")
        assert f['min_drop_pct'] == 10

    def test_drop_pct_with_dash_still_works(self):
        f = parse("-10%")
        assert f['min_drop_pct'] == 10

    def test_drop_pct_boundary_1(self):
        assert parse("1%")['min_drop_pct'] == 1

    def test_drop_pct_boundary_99(self):
        assert parse("99%")['min_drop_pct'] == 99

    def test_dist_lowercase(self):
        assert parse("50km")['dist'] == '50'

    def test_dist_uppercase(self):
        assert parse("50KM")['dist'] == '50'

    def test_all_combined(self):
        f = parse("200-350 50km 15%")
        assert f['min_price'] == '200'
        assert f['max_price'] == '350'
        assert f['dist'] == '50'
        assert f['min_drop_pct'] == 15

    def test_comma_separator_also_works(self):
        f = parse("200-350,50km")
        assert f['min_price'] == '200'
        assert f['dist'] == '50'

    def test_empty_returns_all_none(self):
        f = parse("")
        assert all(v is None for v in f.values())

    def test_pct_zero_raises(self):
        with pytest.raises(ValueError, match="1 y 99"):
            parse("0%")

    def test_pct_100_raises(self):
        with pytest.raises(ValueError, match="1 y 99"):
            parse("100%")

    def test_km_zero_raises(self):
        with pytest.raises(ValueError, match="al menos 1"):
            parse("0km")

    def test_unknown_token_raises(self):
        with pytest.raises(ValueError, match="No entiendo"):
            parse("foobar")

    def test_html_chars_escaped_in_error(self):
        with pytest.raises(ValueError) as exc:
            parse("<script>")
        assert "&lt;script&gt;" in str(exc.value)


class TestIsFilterToken:

    @pytest.mark.parametrize("tok", [
        "200-350", "-350", "200-",
        "50km", "50KM",
        "10%", "-10%", "5%", "99%",
    ])
    def test_returns_true_for_filter_tokens(self, tok):
        assert is_filter(tok) is True

    @pytest.mark.parametrize("tok", [
        "ps5", "nintendo", "switch", "iphone14", "foobar", "200", "-", "",
    ])
    def test_returns_false_for_keywords(self, tok):
        assert is_filter(tok) is False


class TestAutoDetectSplit:
    """Valida la lógica de separación automática keyword/filtros."""

    def _split(self, raw):
        tokens = raw.split()
        filter_tokens = []
        while tokens and TelegramHandlers._is_filter_token(tokens[-1]):
            filter_tokens.insert(0, tokens.pop())
        return ' '.join(tokens), ' '.join(filter_tokens)

    def test_keyword_only(self):
        kws, flt = self._split("ps5")
        assert kws == "ps5"
        assert flt == ""

    def test_keyword_plus_price(self):
        kws, flt = self._split("ps5 200-350")
        assert kws == "ps5"
        assert flt == "200-350"

    def test_multiword_keyword_plus_filters(self):
        kws, flt = self._split("nintendo switch 200-350 50km")
        assert kws == "nintendo switch"
        assert flt == "200-350 50km"

    def test_all_three_filters(self):
        kws, flt = self._split("iphone 15 200-350 50km 10%")
        assert kws == "iphone 15"
        assert flt == "200-350 50km 10%"

    def test_non_filter_in_middle_stops_scan(self):
        # "switch" no es filtro → detiene el escaneo; "200-350" queda como keyword
        kws, flt = self._split("200-350 switch")
        assert kws == "200-350 switch"
        assert flt == ""

    def test_max_price_without_min(self):
        kws, flt = self._split("laptop -500")
        assert kws == "laptop"
        assert flt == "-500"
