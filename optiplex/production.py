import functools
import sqlite3
import csv

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from optiplex.database import get_db
import optiplex.production_model as model

bp = Blueprint('production', __name__, url_prefix='/production')

def todict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
            for key, value in obj.__dict__.items()
            if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj


@bp.route('/', methods=['GET', 'POST'])
def main():
    db = get_db()

    production_json = request.json
    content = {}
    if production_json is not None:
        production = model.from_dict(production_json)
        content['materials'] = decorate_type(production.collect_materials({}), db)
        content['blueprints'] = decorate_type(production.collect_blueprints({}), db)

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
    db = get_db()
    bpo = model.from_db(db, bp_id)
    bpo = model.from_dict(vars(bpo))
    return todict(bpo)


@bp.route('/lookup', methods=['POST'])
def lookup():
    mat_id = request.args.getlist("id")
    db = get_db()
    bpo = model.from_dict(request.json)

    if isinstance(mat_id, list):
        for mid in mat_id:
            bpo.produce_material(db, int(mid))


    return todict(bpo)


@bp.route('/clipboard', methods=['POST'])
def clipboard():
    if request.method == 'POST':
        text = request.json['data']

        db = get_db()

        clip = list(csv.reader(text.replace(',', '').replace('*', '').split('\n'), delimiter='\t'))
        stock = {}
        for entry in clip:
            name = entry[0]
            count = int(entry[1])

            row = db.execute("SELECT id, name FROM typeIDs WHERE name LIKE ?", [name]).fetchone()
            stock[row[0]] = {'id': row[0], 'name': row[1], 'count': count}

        print(stock)
        return stock

    return {}


def decorate_type(types, db: sqlite3.Connection):
    t_list = []
    for k in types:
        name = db.execute("SELECT name FROM typeIDs WHERE id=?;", [k]).fetchone()[0]
        icon = f"Type/{k}_64.png"
        t_list.append({'id': k, 'name': name, 'num': types[k], 'icon': icon})

    return t_list


