import html
import locale
import logging
import re

import telebot

from src.wallbot.database.db_helper import DBHelper
from src.wallbot.database.models import ChatSearch
from src.wallbot.wallapop.api_client import WallapopClient

_PER_PAGE = 5

_MENU_ROUTES = {
    "🔍 Buscar":       'search_command',
    "🔔 Crear alerta": 'add_search',
    "📋 Mis alertas":  'get_searches',
    "📊 Stats":        'get_stats',
    "❓ Ayuda":        'send_help',
}

_HELP_TEXT = (
    "🤖 <b>WallBot</b> — referencia rápida\n"
    "\n"
    "<b>Comandos</b>\n"
    "/add <code>término [filtros]</code> — crea una alerta\n"
    "/search <code>término [filtros]</code> — busca ahora en Wallapop\n"
    "/lis — lista y gestiona tus alertas\n"
    "/del <code>término</code> — elimina una alerta\n"
    "/clear — elimina todas las alertas\n"
    "/stats — estadísticas\n"
    "\n"
    "<b>Filtros de /add</b> — escríbelos después del término:\n"
    "<code>200-350</code> → precio entre 200€ y 350€\n"
    "<code>-350</code>   → hasta 350€\n"
    "<code>200-</code>   → desde 200€\n"
    "<code>50km</code>   → radio de 50 km\n"
    "<code>10%</code>    → avisa solo si baja ≥10%\n"
    "\n"
    "<b>Ejemplos</b>\n"
    "<code>/add ps5</code>\n"
    "<code>/add ps5 200-350</code>\n"
    "<code>/add ps5 200-350 50km</code>\n"
    "<code>/add ps5 10%</code>\n"
    "<code>/add ps5 200-350 50km 10%</code>\n"
)

_ONBOARDING_TEXT = (
    "👋 <b>¡Hola, {name}! Bienvenido a WallBot 🤖</b>\n"
    "\n"
    "Soy tu vigilante de Wallapop. Te aviso cuando:\n"
    "• 🎯 Aparece un artículo nuevo que buscas\n"
    "• 📉 Un artículo que sigues baja de precio\n"
    "\n"
    "<b>🚀 Crea tu primera alerta:</b>\n"
    "\n"
    "<code>/add ps5</code> — sin filtros\n"
    "<code>/add ps5 200-350</code> — precio 200€–350€\n"
    "<code>/add ps5 200-350 50km</code> — + radio 50 km\n"
    "<code>/add ps5 10%</code> — solo si baja ≥10%\n"
    "<code>/add ps5 200-350 50km 10%</code> — todo\n"
    "\n"
    "⏱ Reviso Wallapop cada <b>5 minutos</b>.\n"
    "Usa /help para ver todos los comandos."
)


class TelegramHandlers:
    def __init__(self, bot: telebot.TeleBot, db: DBHelper):
        self.bot = bot
        self.db = db
        self.client = WallapopClient()
        self._searches: dict = {}  # chat_id → {items, page, cs}
        self._register_handlers()

    def _register_handlers(self):
        self.bot.message_handler(commands=['start'])(self.send_onboarding)
        self.bot.message_handler(commands=['help', 'h'])(self.send_help)
        self.bot.message_handler(commands=['add', 'añadir', 'append', 'a'])(self.add_search)
        self.bot.message_handler(commands=['search', 'buscar', 's'])(self.search_command)
        self.bot.message_handler(commands=['del', 'borrar', 'd'])(self.delete_search)
        self.bot.message_handler(commands=['lis', 'listar', 'l'])(self.get_searches)
        self.bot.message_handler(commands=['clear'])(self.clear_searches)
        self.bot.message_handler(commands=['stats', 'estadisticas'])(self.get_stats)
        self.bot.callback_query_handler(func=lambda c: c.data.startswith('del:'))(self.handle_delete_callback)
        self.bot.callback_query_handler(func=lambda c: c.data.startswith('pau:'))(self.handle_pause_callback)
        self.bot.callback_query_handler(func=lambda c: c.data.startswith('res:'))(self.handle_resume_callback)
        self.bot.callback_query_handler(func=lambda c: c.data == 'clearyes')(self.handle_clear_yes)
        self.bot.callback_query_handler(func=lambda c: c.data == 'clearno')(self.handle_clear_no)
        self.bot.callback_query_handler(func=lambda c: c.data.startswith('srch:'))(self.handle_search_callback)
        self.bot.message_handler(func=lambda m: m.text in _MENU_ROUTES)(self.handle_menu_button)

    @staticmethod
    def _main_keyboard():
        kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.add(
            telebot.types.KeyboardButton("🔍 Buscar"),
            telebot.types.KeyboardButton("🔔 Crear alerta"),
            telebot.types.KeyboardButton("📋 Mis alertas"),
            telebot.types.KeyboardButton("📊 Stats"),
            telebot.types.KeyboardButton("❓ Ayuda"),
        )
        return kb

    def handle_menu_button(self, message):
        method_name = _MENU_ROUTES.get(message.text)
        if method_name:
            getattr(self, method_name)(message)

    def send_onboarding(self, message):
        name = html.escape(message.from_user.first_name or "")
        self.bot.send_message(
            message.chat.id,
            _ONBOARDING_TEXT.format(name=name),
            parse_mode='HTML',
            reply_markup=self._main_keyboard()
        )

    def send_help(self, message):
        self.bot.send_message(
            message.chat.id,
            _HELP_TEXT,
            parse_mode='HTML',
            reply_markup=self._main_keyboard()
        )

    @staticmethod
    def _parse_filters(filters_str):
        result = dict(min_price=None, max_price=None, dist=None, min_drop_pct=None)
        tokens = re.split(r'[\s,]+', filters_str.strip())

        for tok in tokens:
            if not tok:
                continue

            # 10% o -10% → bajada mínima
            m = re.fullmatch(r'-?(\d+)%', tok)
            if m:
                pct = int(m.group(1))
                if not 1 <= pct <= 99:
                    raise ValueError(f"⚠️ <code>{html.escape(tok)}</code>: el % debe estar entre 1 y 99.")
                result['min_drop_pct'] = pct
                continue

            # 50km → distancia
            m = re.fullmatch(r'(\d+)km', tok, re.I)
            if m:
                km = int(m.group(1))
                if km < 1:
                    raise ValueError(f"⚠️ <code>{html.escape(tok)}</code>: la distancia debe ser al menos 1 km.")
                result['dist'] = m.group(1)
                continue

            # 200-350 / 200- / -350 → rango de precio
            m = re.fullmatch(r'(\d*)-(\d*)', tok)
            if m and (m.group(1) or m.group(2)):
                result['min_price'] = m.group(1) or None
                result['max_price'] = m.group(2) or None
                continue

            raise ValueError(
                f"⚠️ No entiendo el filtro <code>{html.escape(tok)}</code>.\n"
                "Formatos válidos: <code>200-350</code> · <code>50km</code> · <code>10%</code>"
            )

        return result

    @staticmethod
    def _is_filter_token(tok):
        if re.fullmatch(r'-?(\d+)%', tok):
            return True
        if re.fullmatch(r'(\d+)km', tok, re.I):
            return True
        m = re.fullmatch(r'(\d*)-(\d*)', tok)
        if m and (m.group(1) or m.group(2)):
            return True
        return False

    def add_search(self, message):
        cs = ChatSearch()
        cs.chat_id = message.chat.id
        body = str(message.text).split(' ', 1)
        if len(body) < 2 or not body[1].strip():
            self.bot.send_message(
                message.chat.id,
                "⚠️ Uso: <code>/add término [filtros]</code>\n"
                "Ejemplo: <code>/add ps5 200-350 50km 10%</code>\n\n"
                "Usa /help para ver todos los formatos.",
                parse_mode='HTML'
            )
            return

        raw = body[1].strip()

        if ',' in raw:
            # Separador explícito: todo antes de la primera coma es keyword
            kws_part, filters_part = raw.split(',', 1)
        else:
            # Auto-detección: tokens del final que encajan con patrones de filtro
            tokens = raw.split()
            filter_tokens = []
            while tokens and self._is_filter_token(tokens[-1]):
                filter_tokens.insert(0, tokens.pop())
            kws_part = ' '.join(tokens)
            filters_part = ' '.join(filter_tokens)

        cs.kws = kws_part.strip()
        if not cs.kws:
            self.bot.send_message(
                message.chat.id,
                "⚠️ El término de búsqueda no puede estar vacío.\n"
                "<i>Si tu búsqueda contiene números, usa coma para separar: "
                "<code>/add 200-300,</code></i>",
                parse_mode='HTML'
            )
            return

        if filters_part.strip():
            try:
                f = self._parse_filters(filters_part)
            except ValueError as e:
                self.bot.send_message(message.chat.id, str(e), parse_mode='HTML')
                return
            cs.min_price    = f['min_price']
            cs.max_price    = f['max_price']
            cs.dist         = f['dist']
            cs.min_drop_pct = f['min_drop_pct']

        # Detectar duplicado
        existing = self.db.get_chat_searches(cs.chat_id)
        if any(s.kws.lower() == cs.kws.lower() for s in existing):
            self.bot.send_message(
                message.chat.id,
                f"⚠️ Ya tienes una alerta activa para <b>{html.escape(cs.kws)}</b>.\n"
                "Usa /lis para verla o eliminarla primero.",
                parse_mode='HTML'
            )
            return

        cs.username = message.from_user.username
        cs.name     = message.from_user.first_name
        cs.active   = 1
        logging.info('%s', cs)
        self.db.add_search(cs)

        safe_kws = html.escape(cs.kws)
        lines = [f"✅ <b>Alerta creada</b>\n", f"🔍 {safe_kws}"]
        if cs.min_price or cs.max_price:
            lines.append(f"💰 {cs.min_price or '0'}€ — {cs.max_price or '∞'}€")
        if cs.dist:
            lines.append(f"📍 Radio de {cs.dist} km")
        if cs.min_drop_pct:
            lines.append(f"📊 Avisa si baja ≥{cs.min_drop_pct}%")
        lines.append("\n<i>Te avisaré en el próximo ciclo (≤5 min)</i>")
        self.bot.send_message(message.chat.id, "\n".join(lines), parse_mode='HTML')

    def delete_search(self, message):
        parameters = str(message.text).split(' ', 1)
        if len(parameters) < 2:
            return
        kws = parameters[1].strip()
        if self.db.del_chat_search(message.chat.id, kws):
            self.bot.send_message(
                message.chat.id,
                f"🗑️ Alerta <b>{html.escape(kws)}</b> eliminada.",
                parse_mode='HTML'
            )
        else:
            self.bot.send_message(
                message.chat.id,
                f"⚠️ No encontré ninguna alerta con el término <b>{html.escape(kws)}</b>.\n"
                "Usa /lis para ver tus alertas activas.",
                parse_mode='HTML'
            )

    def clear_searches(self, message):
        searches = self.db.get_chat_searches(message.chat.id)
        n = len(searches)
        if n == 0:
            self.bot.send_message(message.chat.id, "No tienes alertas que borrar.")
            return

        keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            telebot.types.InlineKeyboardButton("✅ Sí, borrar todo", callback_data="clearyes"),
            telebot.types.InlineKeyboardButton("❌ Cancelar",        callback_data="clearno"),
        )
        self.bot.send_message(
            message.chat.id,
            f"⚠️ ¿Seguro que quieres eliminar <b>{n} alerta{'s' if n != 1 else ''}</b>?",
            parse_mode='HTML',
            reply_markup=keyboard
        )

    def get_stats(self, message):
        s = self.db.get_stats(message.chat.id)
        text = (
            "📊 <b>Tus estadísticas</b>\n"
            "\n"
            f"🟢 Alertas activas: <b>{s['active']}</b>\n"
            f"⏸ Alertas pausadas: <b>{s['paused']}</b>\n"
            f"📦 Artículos encontrados: <b>{s['items_found']}</b>\n"
            f"📉 Bajadas de precio: <b>{s['price_drops']}</b>\n"
        )
        self.bot.send_message(message.chat.id, text, parse_mode='HTML')

    def get_searches(self, message):
        searches = self.db.get_chat_searches(message.chat.id)
        if not searches:
            self.bot.send_message(
                message.chat.id,
                "No tienes ninguna alerta activa.\nUsa /add para crear una 👀"
            )
            return

        n = len(searches)
        self.bot.send_message(
            message.chat.id,
            f"📋 <b>{n} alerta{'s' if n != 1 else ''}</b>",
            parse_mode='HTML'
        )
        for search in searches:
            self._send_search_card(message.chat.id, search)

    @staticmethod
    def _build_card(search):
        is_paused = search.active == 2
        icon = "⏸" if is_paused else "🟢"
        status = " <i>(pausada)</i>" if is_paused else ""
        safe_kws = html.escape(search.kws)

        lines = [f"{icon} <b>{safe_kws}</b>{status}"]
        if search.min_price or search.max_price:
            lines.append(f"💰 {search.min_price or '0'}€ — {search.max_price or '∞'}€")
        if search.dist and search.dist != '400':
            lines.append(f"📍 {search.dist} km")
        if search.min_drop_pct:
            lines.append(f"📊 Avisa si baja ≥{search.min_drop_pct}%")

        kws_cb = search.kws[:60]
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        if is_paused:
            keyboard.add(
                telebot.types.InlineKeyboardButton("▶️ Reanudar", callback_data=f"res:{kws_cb}"),
                telebot.types.InlineKeyboardButton("🗑️ Borrar",   callback_data=f"del:{kws_cb}"),
            )
        else:
            keyboard.add(
                telebot.types.InlineKeyboardButton("⏸ Pausar",  callback_data=f"pau:{kws_cb}"),
                telebot.types.InlineKeyboardButton("🗑️ Borrar",  callback_data=f"del:{kws_cb}"),
            )
        return "\n".join(lines), keyboard

    def _send_search_card(self, chat_id, search):
        text, keyboard = self._build_card(search)
        self.bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=keyboard)

    def handle_delete_callback(self, call):
        kws = call.data[4:]
        self.db.del_chat_search(call.message.chat.id, kws)
        self.bot.answer_callback_query(call.id, f"'{kws}' eliminada ✅")
        try:
            self.bot.edit_message_text(
                f"🗑️ <b>{html.escape(kws)}</b> eliminada",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=None
            )
        except Exception as e:
            logging.error(f"Error editando mensaje al borrar: {e}")

    def handle_pause_callback(self, call):
        kws = call.data[4:]
        self.db.pause_search(call.message.chat.id, kws)
        self.bot.answer_callback_query(call.id, f"'{kws}' pausada ⏸")
        self._edit_card_from_db(call, kws)

    def handle_resume_callback(self, call):
        kws = call.data[4:]
        self.db.resume_search(call.message.chat.id, kws)
        self.bot.answer_callback_query(call.id, f"'{kws}' reanudada ▶️")
        self._edit_card_from_db(call, kws)

    def _edit_card_from_db(self, call, kws):
        searches = self.db.get_chat_searches(call.message.chat.id)
        search = next((s for s in searches if s.kws == kws), None)
        if not search:
            return
        text, keyboard = self._build_card(search)
        try:
            self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Error actualizando tarjeta: {e}")

    def handle_clear_yes(self, call):
        self.db.clear_searches(call.message.chat.id)
        self.bot.answer_callback_query(call.id, "Todas las alertas eliminadas ✅")
        try:
            self.bot.edit_message_text(
                "🗑️ Todas las alertas eliminadas.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
        except Exception as e:
            logging.error(f"Error editando mensaje clear: {e}")

    def handle_clear_no(self, call):
        self.bot.answer_callback_query(call.id, "Cancelado")
        try:
            self.bot.edit_message_text(
                "❌ Cancelado.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
        except Exception as e:
            logging.error(f"Error editando mensaje cancel: {e}")

    # ── /search ────────────────────────────────────────────────────────────

    def search_command(self, message):
        body = str(message.text).split(' ', 1)
        if len(body) < 2 or not body[1].strip():
            self.bot.send_message(
                message.chat.id,
                "⚠️ Uso: <code>/search término [filtros]</code>\n"
                "Ejemplo: <code>/search ps5 200-350 50km</code>\n\n"
                "Usa /help para ver los formatos de filtro.",
                parse_mode='HTML'
            )
            return

        raw = body[1].strip()
        if ',' in raw:
            kws_part, filters_part = raw.split(',', 1)
        else:
            tokens = raw.split()
            filter_tokens = []
            while tokens and self._is_filter_token(tokens[-1]):
                filter_tokens.insert(0, tokens.pop())
            kws_part = ' '.join(tokens)
            filters_part = ' '.join(filter_tokens)

        kws = kws_part.strip()
        if not kws:
            self.bot.send_message(message.chat.id, "⚠️ El término no puede estar vacío.")
            return

        cs = ChatSearch(chat_id=message.chat.id, kws=kws)
        if filters_part.strip():
            try:
                f = self._parse_filters(filters_part)
            except ValueError as e:
                self.bot.send_message(message.chat.id, str(e), parse_mode='HTML')
                return
            cs.min_price = f['min_price']
            cs.max_price = f['max_price']
            cs.dist      = f['dist']

        wait = self.bot.send_message(message.chat.id, f"🔍 Buscando <b>{html.escape(kws)}</b>…", parse_mode='HTML')

        try:
            response = self.client.search_items(cs, time_filter=None)
            items = response['data']['section']['payload']['items'] if response else []
        except Exception as e:
            logging.error(f"Error en /search: {e}")
            items = []

        if not items:
            self.bot.edit_message_text(
                f"🔍 Sin resultados para <b>{html.escape(kws)}</b>.",
                message.chat.id, wait.message_id, parse_mode='HTML'
            )
            return

        self._searches[message.chat.id] = {'items': items, 'page': 0, 'cs': cs}
        self._render_search_page(message.chat.id, wait.message_id)

    def _render_search_page(self, chat_id, message_id):
        session = self._searches.get(chat_id)
        if not session:
            return

        items = session['items']
        page  = session['page']
        total = len(items)
        total_pages = (total + _PER_PAGE - 1) // _PER_PAGE
        start = page * _PER_PAGE
        page_items = items[start:start + _PER_PAGE]
        cs = session['cs']

        header = f"🔍 <b>{html.escape(cs.kws)}</b>  ·  {total} resultado{'s' if total != 1 else ''}  ·  pág. {page + 1}/{total_pages}"
        if cs.min_price or cs.max_price:
            header += f"\n💰 {cs.min_price or '0'}€ – {cs.max_price or '∞'}€"
        if cs.dist:
            header += f"  📍 {cs.dist} km"

        blocks = [header]
        for i, item in enumerate(page_items, start=start + 1):
            title = html.escape(item.get('title', ''))
            price = item.get('price', {}).get('amount', 0)
            slug  = item.get('web_slug', '')
            desc  = (item.get('description', '') or '').strip()
            url   = f"https://es.wallapop.com/item/{slug}"

            try:
                price_str = locale.currency(float(price), grouping=True)
            except Exception:
                price_str = f"{float(price):.2f} €"

            lines = [f"<b>{i}.</b> <a href=\"{url}\"><b>{title}</b></a>", f"💰 {price_str}"]
            if desc:
                short = desc[:120].rstrip()
                if len(desc) > 120:
                    short += '…'
                lines.append(f"<i>{html.escape(short)}</i>")
            blocks.append('\n'.join(lines))

        text = '\n\n'.join(blocks)

        nav = []
        if page > 0:
            nav.append(telebot.types.InlineKeyboardButton("◀", callback_data="srch:p"))
        nav.append(telebot.types.InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="srch:_"))
        if page < total_pages - 1:
            nav.append(telebot.types.InlineKeyboardButton("▶", callback_data="srch:n"))

        keyboard = telebot.types.InlineKeyboardMarkup(row_width=3)
        keyboard.row(*nav)
        keyboard.row(
            telebot.types.InlineKeyboardButton("🔔 Monitorizar", callback_data="srch:a"),
            telebot.types.InlineKeyboardButton("✖ Cerrar",       callback_data="srch:c"),
        )

        try:
            self.bot.edit_message_text(
                text, chat_id, message_id,
                parse_mode='HTML',
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        except Exception as e:
            logging.error(f"Error renderizando búsqueda: {e}")

    def handle_search_callback(self, call):
        action  = call.data[5:]
        chat_id = call.message.chat.id

        if action == '_':
            self.bot.answer_callback_query(call.id)
            return

        session = self._searches.get(chat_id)
        if not session:
            self.bot.answer_callback_query(call.id, "Búsqueda expirada, lanza /search de nuevo")
            try:
                self.bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            return

        items       = session['items']
        total_pages = (len(items) + _PER_PAGE - 1) // _PER_PAGE

        if action == 'n' and session['page'] < total_pages - 1:
            session['page'] += 1
            self.bot.answer_callback_query(call.id)
            self._render_search_page(chat_id, call.message.message_id)

        elif action == 'p' and session['page'] > 0:
            session['page'] -= 1
            self.bot.answer_callback_query(call.id)
            self._render_search_page(chat_id, call.message.message_id)

        elif action == 'c':
            del self._searches[chat_id]
            self.bot.answer_callback_query(call.id, "Búsqueda cerrada")
            try:
                self.bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass

        elif action == 'a':
            cs = session['cs']
            existing = self.db.get_chat_searches(chat_id)
            if any(s.kws.lower() == cs.kws.lower() for s in existing):
                self.bot.answer_callback_query(call.id, f"Ya tienes una alerta para '{cs.kws}'")
                return
            new_cs = ChatSearch(
                chat_id=chat_id, kws=cs.kws,
                min_price=cs.min_price, max_price=cs.max_price,
                dist=cs.dist, active=1
            )
            self.db.add_search(new_cs)
            self.bot.answer_callback_query(call.id, f"✅ Alerta creada para '{cs.kws}'")
        else:
            self.bot.answer_callback_query(call.id)
