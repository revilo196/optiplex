import functools


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


@bp.route('/', methods=['GET'])
def main():
    return render_template('production.html')


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
    mat_id = int(request.args.get("id"))
    db = get_db()
    bpo = model.from_dict(request.json)
    bpo.produce_material(db, mat_id)
    return todict(bpo)
