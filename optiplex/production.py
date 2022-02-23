import copy
import csv

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from optiplex.database import get_db
import optiplex.production_model as model

bp = Blueprint('production', __name__, url_prefix='/production')


@bp.route('/', methods=['GET'])
def prod():
    content = {}

    if 'production' in session:
        production = copy.deepcopy(session['production'])    # dont chage the main object
        if 'stock' in session:
            stock = copy.deepcopy(session['stock'])
            production.update_vs_stock(stock)

        content['materials'] = list(production.collect_materials({}).values())
        content['materials'].sort(key=lambda x: x['depth'])
        content['blueprints'] = list(production.collect_blueprints({}).values())
        content['blueprints'].sort(key=lambda x: x['depth'])

    return render_template('production.html', content=content)


@bp.route('/search', methods=['GET'])
def find():
    s = request.args.get("s")
    db = get_db()

    options = db.execute("""SELECT b.id, tID.name  FROM typeIDs
                INNER JOIN blueprints b on typeIDs.id = b.product_typeID
                INNER JOIN typeIDs tID on tID.id = b.id
                WHERE tID.name LIKE ?;""", ["%"+s+"%"]).fetchmany(5)
    result = {}
    for o in options:
        result[o[0]] = o[1]
    return result


@bp.route('/blueprint', methods=['GET'])
def blueprint():
    bp_id = int(request.args.get("id"))
    me = (100 - int(request.args.get("me"))) / 100
    runs = int(request.args.get("runs"))

    db = get_db()
    bpo = model.from_db(db, bp_id, me, runs)
    session['production'] = bpo
    return {}


@bp.route('/lookup', methods=['GET'])
def lookup():
    mat_id = request.args.getlist("id")
    me = (100 - int(request.args.get("me"))) / 100
    db = get_db()
    bpo = session['production']

    for mid in mat_id:
        bpo.produce_material(db, int(mid), me=me)

    session['production'] = bpo
    return {}


@bp.route('/clipboard', methods=['POST', 'DELETE'])
def clipboard():
    if request.method == 'POST':
        text = request.json['data']
        db = get_db()

        clip = list(csv.reader(text.replace(',', '').replace('*', '').split('\n'), delimiter='\t'))
        if 'stock' in session:
            stock = session['stock']
        else:
            stock = {}

        for entry in clip:
            name = entry[0]
            count = int(entry[1])

            row = db.execute("SELECT id, name, group_id FROM typeIDs WHERE name LIKE ?", [name]).fetchone()
            if row[0] in stock:
                stock[row[0]]['count'] += count
            else:
                stock[row[0]] = {'id': row[0], 'name': row[1], 'count': count, 'gid': row[2]}

        print(stock)
        session['stock'] = stock
        return stock

    if request.method == 'DELETE' and 'stock' in session:
        session.pop('stock')

    return {}

