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


@bp.route('/blueprint/save', methods=['GET'])
def blueprint_save():
    db = get_db()
    pickle_production = pickle.dumps(session['production'])
    pickle_production_compressed = zlib.compress(pickle_production)
    prod_hash = hashlib.sha1(pickle_production_compressed).digest()[:7]
    key = int.from_bytes(prod_hash, byteorder='big')
    url_code = base64.urlsafe_b64encode(prod_hash)

    db.execute("REPLACE INTO stored_production VALUES (?,?)", [key, pickle_production_compressed])
    db.commit()

    return render_template('modal_saved.html', name="production", url_code_str="p="+url_code.decode('utf-8'))


@bp.route('/load', methods=['GET'])
def blueprint_load():
    db = get_db()

    if 'p' in request.args:
        url_code = request.args.get("p")
        key = b64url_to_key(url_code)

        compressed = db.execute("SELECT object FROM stored_production WHERE key == ?", [key]).fetchone()[0]
        pickled = zlib.decompress(compressed)
        production = pickle.loads(pickled)
        session['production'] = production

    if 's' in request.args:
        url_code = request.args.get("s")
        key = b64url_to_key(url_code)

        compressed = db.execute("SELECT object FROM stored_production WHERE key == ?", [key]).fetchone()[0]
        pickled = zlib.decompress(compressed)
        stock = pickle.loads(pickled)
        session['stock'] = stock

    return render_template('redirect.html', url=url_for('.prod'))


@bp.route('/lookup', methods=['GET'])
def lookup():
    mat_id = request.args.getlist("id")
    me = 1.0
    if 'me' in request.args:
        me = (100 - int(request.args.get("me"))) / 100
    db = get_db()
    bpo = session['production']

    bp_rm_id = request.args.getlist('rm')

    for mid in mat_id:
        bpo.produce_material(db, int(mid), me=me)

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
    pickle_stock = pickle.dumps(session['stock'])
    pickle_stock_compressed = zlib.compress(pickle_stock)
    prod_hash = hashlib.sha1(pickle_stock_compressed).digest()[:7]
    key = int.from_bytes(prod_hash, byteorder='big')
    url_code = base64.urlsafe_b64encode(prod_hash)

    db.execute("REPLACE INTO stored_production VALUES (?,?)", [key, pickle_stock_compressed])
    db.commit()

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
