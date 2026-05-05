class ChatSearch:

    def __init__(self, chat_id=None, kws=None, cat_ids=None, min_price=None, max_price=None,
                 dist=None, publish_date=None, orde=None, username=None, name=None, active=None,
                 min_drop_pct=None):
        self.chat_id = chat_id
        self.kws = kws
        self.cat_ids = cat_ids
        self.min_price = min_price
        self.max_price = max_price
        self.dist = dist
        self.publish_date = publish_date
        self.orde = orde
        self.username = username
        self.name = name
        self.active = active
        self.min_drop_pct = min_drop_pct

    def __str__(self) -> str:
        return "<ChatSearch chat_id:%s kws:%s min_price:%s max_price:%s dist:%s min_drop_pct:%s active:%s>" % \
            (self.chat_id, self.kws, self.min_price, self.max_price,
             self.dist, self.min_drop_pct, self.active)


class Item:
    def __init__(self, item_id, chat_id, title, price, url, publish_date, observaciones, item):
        self.item_id = item_id
        self.chat_id = chat_id
        self.title = title
        self.price = price
        self.url = url
        self.publish_date = publish_date
        self.observaciones = observaciones
        self.item = item
