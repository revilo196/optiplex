import math
import sqlite3


def find_bp_from_product(db: sqlite3.Connection, p_id) -> int:
    bp_id = db.execute("""SELECT bp.id FROM blueprints AS bp WHERE product_typeID == ?""", [p_id]).fetchone()
    return bp_id[0]


class ProdBlueprint(object):

    def __init__(self, bp_id: int, name: str, product, materials, me: float = 1.0, runs: int = 1):
        self.id = bp_id
        self.name = name
        self.product = product
        self.materials = materials
        self.runs = runs
        self.me = me

    def produce_material(self, db, mat_id: int, me: float = 1.0):
        for (i, m) in enumerate(self.materials):
            # recursive function if material is already produced
            if 'bp' in m:
                m['bp'].produce_material(db, mat_id, me=me)
            else:
                if m['id'] == mat_id:
                    # replace type with Production
                    bp_id = find_bp_from_product(db, mat_id)
                    pr = from_db(db, bp_id, me=me)
                    needed = int(math.ceil(m['num']*self.runs*self.me))
                    pr.runs = int(math.ceil(needed / pr.product['num']))
                    self.materials[i]['bp'] = pr

    def update_runs(self, runs):
        self.runs = runs
        for m in self.materials:
            if 'bp' in m:
                needed = int(math.ceil(m['num'] * self.runs * self.me))
                m_runs = int(math.ceil(needed / m['bp'].product['num']))
                m['bp'].update_runs(m_runs)

    def collect_materials(self, collected):
        for m in self.materials:
            if 'bp' in m:
                collected = m['bp'].collect_materials()
            else:
                needed = int(math.ceil(m['num'] * self.runs * self.me))
                if m['num'] not in collected:
                    collected[m['num']] = 0
                collected[m['num']] += needed

        return collected




def from_db(db: sqlite3.Connection, bp_id: int, me: float = 1.0, runs: int = 1) -> ProdBlueprint:
    c = db.cursor()
    bp = c.execute("""SELECT blueprints.id, bpID.name
                        FROM blueprints
                        INNER JOIN typeIDs bpID on bpID.id = blueprints.id
                        WHERE blueprints.id = ? ;""", [bp_id]).fetchone()

    p = c.execute("""SELECT product_typeID,product_quantity, name ,group_id,filename, ep.adjusted_price FROM blueprints
                                INNER JOIN typeIDs tID on tID.id = blueprints.product_typeID
                                LEFT OUTER JOIN  icons i on tID.iconID = i.iconID
                                INNER JOIN esi_prices ep on tID.id = ep.typeID
                                WHERE blueprints.id=? ;""", [bp_id]).fetchone()

    product = {'id': p[0], 'num': p[1], 'name': p[2], 'gid': p[3], 'icon': p[4], 'adju': p[5]}

    mats = c.execute("""SELECT tID.id, group_id, material_quantity, name, filename, ep.adjusted_price FROM blueprint_materials
                        INNER JOIN typeIDs tID on tID.id == blueprint_materials.material_id
                        INNER JOIN icons i on tID.iconID = i.iconID
                        INNER JOIN esi_prices ep on tID.id = ep.typeID
                        WHERE blueprint_id = ?;""", [bp_id]).fetchall()

    materials = []
    for m in mats:
        m_obj = {'id': m[0], 'gid': m[1], 'num': m[2], 'name': m[3], 'icon': m[4], 'adju': m[5]}
        materials.append(m_obj)

    return ProdBlueprint(bp[0], bp[1], product, materials, me, runs)


def from_dict(data) -> ProdBlueprint:
    for (k, m) in enumerate(data['materials']):
        if 'bp' in m:
            data['materials'][k]['bp'] = from_dict(m['bp'])

    return ProdBlueprint(data['id'], data['name'], data['product'], data['materials'], data['me'], data['runs'])


