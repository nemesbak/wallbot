import html
import locale
import logging


def _format_description(description):
    if not description or not description.strip():
        return ''
    desc = description.strip()
    if len(desc) > 150:
        desc = desc[:150].rstrip() + '…'
    return f"\n<i>{html.escape(desc)}</i>"


def notel(bot, chat_id, price, title, url_item, old_price=None, price_history=None, image_url=None, description=None):
    url = f"https://es.wallapop.com/item/{url_item}"
    price_str = locale.currency(price, grouping=True)
    safe_title = html.escape(title)
    desc_line = _format_description(description)

    if old_price is not None:
        reduction_pct = round((1 - price / old_price) * 100)
        old_price_str = locale.currency(old_price, grouping=True)
        text = (
            f"❗ <b>{safe_title}</b>{desc_line}\n"
            f"📉 {price_str} <b>(-{reduction_pct}%)</b>\n"
            f"<s>{old_price_str}</s>\n"
            f'<a href="{url}">🔗 Ver en Wallapop</a>'
        )
    else:
        text = (
            f"🎯 <b>{safe_title}</b>{desc_line}\n"
            f"💰 {price_str}\n"
            f'<a href="{url}">🔗 Ver en Wallapop</a>'
        )

    try:
        if image_url:
            bot.send_photo(chat_id, image_url, caption=text, parse_mode='HTML')
        else:
            bot.send_message(chat_id, text, parse_mode='HTML')
    except Exception:
        # fallback a texto si la foto falla
        try:
            bot.send_message(chat_id, text, parse_mode='HTML')
        except Exception as e:
            logging.error(f"Error enviando notificación a {chat_id}: {e}")
