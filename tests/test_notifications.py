import pytest
from unittest.mock import MagicMock, patch
from src.wallbot.telegram.notifications import notel, _format_description


@pytest.fixture(autouse=True)
def mock_locale():
    with patch('src.wallbot.telegram.notifications.locale') as loc:
        loc.currency.side_effect = lambda v, **kw: f"{v:.2f} €"
        yield loc


class TestFormatDescription:

    def test_none_returns_empty(self):
        assert _format_description(None) == ''

    def test_empty_string_returns_empty(self):
        assert _format_description('') == ''
        assert _format_description('   ') == ''

    def test_short_description_unchanged(self):
        result = _format_description("Artículo en buen estado")
        assert "Artículo en buen estado" in result
        assert result.startswith("\n<i>")

    def test_long_description_truncated(self):
        long = "x" * 200
        result = _format_description(long)
        assert "…" in result
        assert len(result) < len(long) + 20

    def test_html_chars_escaped(self):
        result = _format_description("<b>bold</b>")
        assert "<b>" not in result
        assert "&lt;b&gt;" in result


class TestNotel:

    def test_new_item_with_image_sends_photo(self):
        bot = MagicMock()
        notel(bot, "123", 100.0, "PS5", "ps5-slug", image_url="http://img.jpg")
        bot.send_photo.assert_called_once()
        bot.send_message.assert_not_called()

    def test_new_item_without_image_sends_message(self):
        bot = MagicMock()
        notel(bot, "123", 100.0, "PS5", "ps5-slug")
        bot.send_message.assert_called_once()
        bot.send_photo.assert_not_called()

    def test_new_item_contains_title(self):
        bot = MagicMock()
        notel(bot, "123", 100.0, "Mi PS5 Pro", "slug")
        text = bot.send_message.call_args[0][1]
        assert "Mi PS5 Pro" in text

    def test_new_item_contains_url(self):
        bot = MagicMock()
        notel(bot, "123", 100.0, "PS5", "ps5-new-slug")
        text = bot.send_message.call_args[0][1]
        assert "ps5-new-slug" in text

    def test_new_item_icon(self):
        bot = MagicMock()
        notel(bot, "123", 100.0, "PS5", "slug")
        assert "🎯" in bot.send_message.call_args[0][1]

    def test_description_appears_in_message(self):
        bot = MagicMock()
        notel(bot, "123", 100.0, "PS5", "slug", description="Consola en perfecto estado")
        text = bot.send_message.call_args[0][1]
        assert "Consola en perfecto estado" in text

    def test_no_description_no_extra_line(self):
        bot = MagicMock()
        notel(bot, "123", 100.0, "PS5", "slug")
        text = bot.send_message.call_args[0][1]
        assert "<i>" not in text

    def test_price_drop_shows_reduction_pct(self):
        bot = MagicMock()
        notel(bot, "123", 80.0, "PS5", "slug", old_price=100.0)
        text = bot.send_message.call_args[0][1]
        assert "-20%" in text

    def test_price_drop_icon(self):
        bot = MagicMock()
        notel(bot, "123", 80.0, "PS5", "slug", old_price=100.0)
        assert "📉" in bot.send_message.call_args[0][1]

    def test_price_drop_with_description(self):
        bot = MagicMock()
        notel(bot, "123", 80.0, "PS5", "slug", old_price=100.0, description="Buen estado")
        text = bot.send_message.call_args[0][1]
        assert "Buen estado" in text
        assert "-20%" in text

    def test_html_escaping_title(self):
        bot = MagicMock()
        notel(bot, "123", 100.0, "<script>xss</script>", "slug")
        text = bot.send_message.call_args[0][1]
        assert "<script>" not in text
        assert "&lt;script&gt;" in text

    def test_photo_failure_falls_back_to_message(self):
        bot = MagicMock()
        bot.send_photo.side_effect = Exception("timeout")
        notel(bot, "123", 100.0, "PS5", "slug", image_url="http://img.jpg")
        bot.send_message.assert_called_once()

    def test_parse_mode_is_html(self):
        bot = MagicMock()
        notel(bot, "123", 100.0, "PS5", "slug")
        assert bot.send_message.call_args[1].get('parse_mode') == 'HTML'
