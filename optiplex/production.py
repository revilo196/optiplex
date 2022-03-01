import copy
import csv
import pickle
import base64
import zlib
import hashlib
import math
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, abort
)

from optiplex.database import get_db
import optiplex.production_model as model

bp = Blueprint('production', __name__, url_prefix='/production')


@bp.app_template_global()
def round_to_int(x):
    return int(round(x))


@bp.app_template_global()
def isk_format(x: float):
    return f"{x:,.2f} ISK"


def b64url_to_key(url_code):
    prod_hash = base64.urlsafe_b64decode(url_code)
    key = int.from_bytes(prod_hash, byteorder='big')
    return key


def hash_to_b64url(hash_bytes):
    # key = int.from_bytes(hash_bytes[:7], byteorder='big')
    url_code = base64.urlsafe_b64encode(hash_bytes[:7])
    return url_code


@bp.route('/', methods=['GET'])
def prod():
    content = {}
    total_job_cost = 0
    remaining_job_cost = 0
    if 'production' in session:
        production = copy.deepcopy(session['production'])  # dont change the main object
        total_job_cost = production.sum_job_costs()
        if 'stock' in session:
            stock = copy.deepcopy(session['stock'])
            production.update_vs_stock(stock)

        remaining_job_cost = production.sum_job_costs()

        content['materials'] = list(production.collect_materials({}).values())
        content['materials'].sort(key=lambda x: x['depth'])
        content['blueprints'] = list(production.collect_blueprints({}).values())
        content['blueprints'].sort(key=lambda x: x['depth'])

    return render_template('production.html', content=content,
                           total_job_cost=total_job_cost, remaining_job_cost=remaining_job_cost)


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
    me = int(request.args.get("me"))
    runs = int(request.args.get("runs"))
    station = int(request.args.get("sta"))
    rig = float(request.args.get("rig"))
    sec = request.args.get("sec")
    index = float(request.args.get("index"))

    db = get_db()
    final_me = model.calculate_final_me(station, rig, me, sec, model.get_bp_group(db, bp_id))
    bpo = model.from_db(db, bp_id, final_me, runs, index)
    session['production'] = bpo
    return {}


def store_object(db, obj) -> bytes:
    dump = pickle.dumps(obj)
    compressed = zlib.compress(dump)
    hash_key = hashlib.sha1(compressed).digest()[:7]
    key = int.from_bytes(hash_key, byteorder='big')
    url_code = base64.urlsafe_b64encode(hash_key)
    db.execute("REPLACE INTO stored_production VALUES (?,?)", [key, compressed])
    db.commit()

    return url_code


@bp.route('/blueprint/save', methods=['GET'])
def blueprint_save():
    db = get_db()
    url_code = store_object(db, session['production'])

    return render_template('modal_saved.html', name="production", url_code_str="p="+url_code.decode('utf-8'))


def load_obj(db, url_code: str):
    key = b64url_to_key(url_code)
    compressed = db.execute("SELECT object FROM stored_production WHERE key == ?", [key]).fetchone()[0]
    pickled = zlib.decompress(compressed)
    obj = pickle.loads(pickled)
    return obj


@bp.route('/load', methods=['GET'])
def blueprint_load():
    db = get_db()

    if 'p' in request.args:
        url_code = request.args.get("p")
        session['production'] = load_obj(db, url_code)

    if 's' in request.args:
        url_code = request.args.get("s")
        session['stock'] = load_obj(db, url_code)

    return render_template('redirect.html', url=url_for('.prod') )


@bp.route('/lookup', methods=['GET'])
def lookup():
    mat_id = request.args.getlist("id")
    bp_rm_id = request.args.getlist('rm')

    me = 0
    station = 0
    rig = 0
    index = 5.0
    sec = 'High'

    if 'me' in request.args:
        me = int(request.args.get("me"))
    if 'sta' in request.args:
        station = int(request.args.get("sta"))
    if 'rig' in request.args:
        rig = float(request.args.get("rig"))
    if 'sec' in request.args:
        sec = request.args.get("sec")
    if 'index' in request.args:
        index = float(request.args.get("index"))

    db = get_db()
    bpo = session['production']

    for mid in mat_id:
        bp_id = model.find_bp_from_product(db, mid)
        final_me = model.calculate_final_me(station, rig, me, sec, model.get_bp_group(db, bp_id))
        bpo.produce_material(db, int(mid), me=final_me, index=index)

    for bp_id in bp_rm_id:
        bpo.remove_bp(int(bp_id))

    session['production'] = bpo
    return {}


@bp.route('/stock', methods=['GET', 'POST', 'DELETE'])
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

    if request.method == 'GET':
        return session['stock']

    return {}


@bp.route('/stock/item', methods=['DELETE'])
def stock_item():
    if request.method == 'DELETE' and 'stock' in session:
        if 'id' in request.args:
            itemId = int(request.args.get('id'))
            if itemId in session['stock']:
                session['stock'].pop(itemId)
                return "OK"

    return abort(400)


@bp.route('/stock/save', methods=['GET'])
def clipboard_save():
    db = get_db()
    url_code = store_object(db, session['stock'])

    return render_template('modal_saved.html', name="stock", url_code_str="s="+url_code.decode('utf-8'))


@bp.route('/admin/save_example', methods=['GET'])
def admin_example():

    if 'key' in request.args:
        if request.args['key'] != 'some_admin_key':
            return abort(403)

        db = get_db()

        if 'p' in request.args:
            # save p as example key
            url_code = request.args.get("p")
            key = b64url_to_key(url_code)
            compressed = db.execute("SELECT object FROM stored_production WHERE key == ?", [key]).fetchone()[0]
            key_example = b64url_to_key("PrdExample==".encode('UTF-8'))
            db.execute("REPLACE INTO stored_production VALUES (?,?)", [key_example, compressed])
            db.commit()

        if 's' in request.args:
            # save p as example key
            url_code = request.args.get("s")
            key = b64url_to_key(url_code)
            compressed = db.execute("SELECT object FROM stored_production WHERE key == ?", [key]).fetchone()[0]

            key_example = b64url_to_key("StoExample==".encode('UTF-8'))
            db.execute("REPLACE INTO stored_production VALUES (?,?)", [key_example, compressed])
            db.commit()

        return "OK"

    return abort(403)
