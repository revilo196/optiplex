import requests


def fetch_prices(typeIDs, conn):
    c = conn.cursor()
    for ids in typeIDs:
        response = requests.get(f"https://esi.evetech.net/latest/markets/10000002/orders/?datasource=tranquility&order_type=buy&type_id={ids}")
        response = response.json()
        prices = sorted([entry['price'] for entry in response])
        price_buy = sum(prices[-5:]) / 5

        response = requests.get(f"https://esi.evetech.net/latest/markets/10000002/orders/?datasource=tranquility&order_type=sell&type_id={ids}")
        response = response.json()
        prices = sorted([entry['price'] for entry in response])
        price_sell = sum(prices[0:5]) / 5
        c.execute("REPLACE INTO market_prices VALUES(?, ?, ?);", (ids, price_buy, price_sell))
    conn.commit()


def fetch_reactions_prices(conn_, reporter=None):
    # fetch Market data Jita
    cc = conn_.cursor()
    materials = cc.execute(
        "SELECT id FROM typeIDs WHERE group_id == 427 OR group_id == 1136;").fetchall()
    composites = cc.execute("SELECT id FROM typeIDs WHERE group_id == 429;").fetchall()

    fetch_prices([m[0] for m in materials], conn_)
    fetch_prices([cx[0] for cx in composites], conn_)


def fetch_adjust_price(conn):
    response = requests.get("https://esi.evetech.net/dev/markets/prices/?datasource=tranquility")
    response = response.json()

    for elem in response:
        item = elem['type_id']
        adjust = None
        aver = None
        if 'adjusted_price' in elem:
            adjust = elem['adjusted_price']

        if 'average_price' in elem:
            aver = elem['average_price']
        conn.execute("REPLACE INTO esi_prices(typeID, adjusted_price, average_price) VALUES(?, ?, ?);", (item, adjust, aver))

    conn.commit()

