import requests


def fetch_prices(typeIDs, outputs, conn):
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
        outputs['text'] = f"{ids}, buy:{price_buy:.0f}, sell:{price_sell:.0f})"
        c.execute("REPLACE INTO prices VALUES(?, ?, ?);", (ids, price_buy, price_sell))
    conn.commit()


def fetch_all_prices(conn_, reporter=None):
    # fetch Market data Jita for all Composite and Moon Mats not for Immidiat products
    if reporter is None:
        reporter = {}

    cc = conn_.cursor()
    materials = cc.execute(
        "SELECT id FROM typeIDs WHERE group_id == 427 OR group_id == 1136;").fetchall()
    composites = cc.execute("SELECT id FROM typeIDs WHERE group_id == 429;").fetchall()

    fetch_prices([m[0] for m in materials], reporter, conn_)
    fetch_prices([cx[0] for cx in composites], reporter, conn_)
    reporter['text'] = ""

