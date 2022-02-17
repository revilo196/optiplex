from flask import Flask
from flask import render_template
from flask import request
import csv
from . import create_app
from .database import get_db
import numpy as np
from .composite_optimizer import CompositeOptimizer, get_optimizer

app = create_app()


@app.route('/')
def main():
    db = get_db()
    items = db.execute("SELECT id, name, group_id, i.filename FROM typeIDs INNER JOIN icons i on typeIDs.iconID = i.iconID WHERE group_id == 427 OR group_id == 1136;").fetchall()
    composite = db.execute("SELECT id, name, group_id, i.filename FROM typeIDs INNER JOIN icons i on typeIDs.iconID = i.iconID WHERE group_id == 429")
    return render_template('page.html', input_items=items, output_items=composite)


@app.route('/clipboard_process', methods=['POST'])
def clipboard():
    if request.method == 'POST':
        text = request.form['clipboard']

        db = get_db()
        mats = db.execute("SELECT id, name FROM typeIDs WHERE group_id=427").fetchall()

        clip = list(csv.reader(text.replace(',', '').split('\n'), delimiter='\t'))
        out = {}
        for entry in clip:
            name = entry[0]
            count = int(entry[1])
            for m in mats:
                if m[1] == name:
                    out[m[0]] = count
        return out

    return {}


@app.route('/process_value', methods=['POST'])
def process_value():
    if request.method == 'POST':
        data = request.json
        print(data)

        db = get_db()

        running_sum = 0
        for (k,v) in data.items():
            value = db.execute("SELECT sell FROM prices WHERE typeID = ?", [int(k)]).fetchone()[0]
            running_sum += int(v) * value
        return {'value': running_sum}

    return {}


def pack_materials(material_vec: np.ndarray, opti:  CompositeOptimizer):
    assert len(material_vec) == len(opti.lookup)

    materials = {}
    for (ids, idx) in opti.lookup.items():
        materials[ids] = material_vec[idx]

    return materials


def pack_products(products_vec: np.ndarray, opti:  CompositeOptimizer):
    assert len(products_vec) == len(opti.lookup_product)

    products = {}
    for (ids, idx) in opti.lookup_product.items():
        products[ids] = products_vec[idx]

    return products


@app.route('/optimize', methods=['POST'])
def optimize():
    data = request.json['mats']
    methode = request.json['meth']
    print(data)
    opti = get_optimizer()

    # create stock_vector
    stock = np.ones((len(opti.lookup),))
    for (k,v) in data.items():
        stock[opti.lookup[int(k)]] = int(v)

    if methode == 'value':
        pass
    elif methode == 'profit':
        opti.objective_profit()
    elif methode == 'total':
        opti.objective_total(stock)
    elif methode == 'usage':
        opti.objective_usage(stock)

    x = opti.optimize_multipass(stock)
    print(x)
    x = np.floor(x/2)*2

    residuals = stock - np.array(opti.runs_to_materials(x)).flatten()
    residuals[0] = 1
    residuals[1] = 1
    residuals[2] = 1
    residuals[3] = 1

    x2r = opti.optimize_residual(np.floor(residuals))
    x2r = np.floor(x2r/2)*2

    x = x + x2r

    print(opti.runs_to_materials(x))
    products = pack_products(opti.runs_to_products(x), opti)
    prices = opti.runs_to_products_prices(x)
    price_sum = np.sum(prices)
    prices = pack_products(prices, opti)
    materials = pack_materials(np.array(opti.runs_to_materials(x)).flatten(), opti)
    costs = np.sum(opti.runs_to_materials_prices(x))
    num_used = np.sum(np.array(opti.runs_to_materials(x)).flatten())
    num_stock = np.sum(stock)
    runs = pack_products(x, opti)

    return {'runs': runs, 'materials': materials, 'product': products, 'prices': prices,
            'costs': costs, 'price': price_sum, 'num_used': num_used, 'num_stock': num_stock}


if __name__ == '__main__':
    app.run()
