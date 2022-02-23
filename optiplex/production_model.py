import math
import sqlite3


def find_bp_from_product(db: sqlite3.Connection, p_id) -> int:
    bp_id = db.execute("""SELECT bp.id FROM blueprints AS bp WHERE product_typeID == ?""", [p_id]).fetchone()
    return bp_id[0]


class ProdBlueprint(object):

    def __init__(self, bp_id: int, name: str, product: dict, materials: list, me: float = 1.0, runs: int = 1):
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

    def update_vs_stock(self, stock: dict):
        if self.runs > 0:
            for m in self.materials:
                if m['id'] in stock:
                    needed = int(math.ceil(m['num'] * self.runs * self.me))
                    r = stock[m['id']]['count'] - needed
                    if r > 0:
                        stock[m['id']]['count'] = r
                        needed = 0  # or self.materials.remove(m)
                    else:
                        stock.pop(m['id'])  # or stock[m['id']] = 0
                        needed = -r
                    m['num'] = needed / (self.runs * self.me)  # reapply to number needed
                    if 'bp' in m:
                        m_runs = int(math.ceil(needed / m['bp'].product['num']))
                        m['bp'].update_runs(m_runs)

                if 'bp' in m:
                    stock = m['bp'].update_vs_stock(stock)

        return stock

    def collect_materials(self, collected, i: int = 0):
        for m in self.materials:
            if 'bp' in m:
                collected = m['bp'].collect_materials(collected, i+1)
            else:
                needed = int(math.ceil(m['num'] * self.runs * self.me))
                if m['id'] not in collected:
                    collected[m['id']] = {'name': m['name'], 'id': m['id'], 'num': 0}
                collected[m['id']]['num'] += needed
                collected[m['id']]['depth'] = i

        return collected

    def collect_blueprints(self, collected, i: int = 0):

        if self.id not in collected:
            collected[self.id] = {'name': self.name, 'runs': 0, 'id': self.id}

        collected[self.id]['runs'] += self.runs
        collected[self.id]['depth'] = i

        for m in self.materials:
            if 'bp' in m:
                collected = m['bp'].collect_blueprints(collected, i+1)
        return collected

    def collect_materials_steps(self, i: int = 0):
        # list of collected values
        collected = []
        # dict used to sum values with same id from the same depth
        depth = {}
        for m in self.materials:
            if 'bp' in m:
                sub = m['bp'].collect_materials(i + 1)
                # sum 'num' with the same id from the same depth
                for s in sub:
                    if s['depth'] not in depth:
                        depth[s['depth']] = {}
                    if s['id'] not in depth[s['depth']]:
                        depth[s['depth']][s['id']] = s
                    else:
                        depth[s['depth']][s['id']]['num'] += s['num']

            else:
                needed = int(math.ceil(m['num'] * self.runs * self.me))
                collected.append({'id': m['id'], 'name': m['name'], 'num': needed, 'depth': i})

        # collect summarized values from bellow
        for d in depth.values():
            for mat in d.values():
                collected.append(mat)

        return collected

    def collect_blueprints_steps(self, i: int = 0):
        collected = [{'id': self.id, 'name': self.name, 'runs': self.runs, 'depth': i}]
        i += 1
        for m in self.materials:
            if 'bp' in m:
                collected = collected + m['bp'].collect_blueprints(i)
        return collected


def from_db(db: sqlite3.Connection, bp_id: int, me: float = 1.0, runs: int = 1) -> ProdBlueprint:
    c = db.cursor()
    bp = c.execute("""SELECT blueprints.id, bpID.name
                        FROM blueprints
                        INNER JOIN typeIDs bpID on bpID.id = blueprints.id
                        WHERE blueprints.id = ? ;""", [bp_id]).fetchone()

    p = c.execute("""SELECT product_typeID,product_quantity, name ,group_id, ep.adjusted_price FROM blueprints
                                INNER JOIN typeIDs tID on tID.id = blueprints.product_typeID
                                INNER JOIN esi_prices ep on tID.id = ep.typeID
                                WHERE blueprints.id=? ;""", [bp_id]).fetchone()

    product = {'id': p[0], 'num': p[1], 'name': p[2], 'gid': p[3], 'adju': p[4]}

    mats = c.execute("""SELECT tID.id, group_id, material_quantity, name, ep.adjusted_price FROM blueprint_materials
                        INNER JOIN typeIDs tID on tID.id == blueprint_materials.material_id
                        INNER JOIN esi_prices ep on tID.id = ep.typeID
                        WHERE blueprint_id = ?;""", [bp_id]).fetchall()

    materials = []
    for m in mats:
        m_obj = {'id': m[0], 'gid': m[1], 'num': m[2], 'name': m[3], 'adju': m[4]}
        materials.append(m_obj)

    return ProdBlueprint(bp[0], bp[1], product, materials, me, runs)


def from_dict(data) -> ProdBlueprint:
    for (k, m) in enumerate(data['materials']):
        if 'bp' in m:
            data['materials'][k]['bp'] = from_dict(m['bp'])

    return ProdBlueprint(data['id'], data['name'], data['product'], data['materials'], data['me'], data['runs'])


