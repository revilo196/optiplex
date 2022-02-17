import sqlite3
import yaml
from .util import fetch_all_prices
from pathlib import Path

def create_tables(con: sqlite3.Connection):
    c = con.cursor()
    with open("create_tables.sql") as f:
        c.executescript(f.read())


def load_groups(con: sqlite3.Connection):
    c = con.cursor()
    with open('import/groupIDs.yaml', 'r') as file:
        print("file_opened -- starting reading")
        groups_db = yaml.load(file, Loader=yaml.CLoader)
        print("done loading")
        groups = [(i, group['name']['en']) for (i, group) in groups_db.items() if 'en' in group['name']]
        print(groups)
        c.executemany('INSERT INTO groupIDs VALUES(?,?);', groups)
        con.commit()


def load_icons(con: sqlite3.Connection):
    c = con.cursor()
    with open('import/iconIDs.yaml', 'r') as file:
        print("file_opened -- starting reading")
        icons_db = yaml.load(file, Loader=yaml.CLoader)
        print("done loading")
        icons = [(i, Path(group['iconFile']).name) for (i, group) in icons_db.items()]
        c.executemany('INSERT INTO icons VALUES(?,?);', icons)



def load_types(con):
    c = con.cursor()
    with open('import/typeIDs.yaml', 'r') as file:
        print("file_opened -- starting reading")
        types_db = yaml.load(file, Loader=yaml.CLoader)
        print("done loading")
        types = [(i, ty['name']['en'], ty['groupID'], ty['iconID']) for (i, ty) in types_db.items() if 'en' in ty['name'] and 'iconID' in ty]
        print(types)
        c.executemany('INSERT INTO typeIDs VALUES(?,?,?,?);', types)
        con.commit()


def load_blueprints(con):
    c = con.cursor()
    with open('import/blueprints.yaml', 'r') as file:
        blueprints = yaml.load(file, Loader=yaml.CLoader)

        for (i, blu) in blueprints.items():
            if "reaction" in blu['activities']:
                product = blu['activities']['reaction']['products'][0]
                materials = blu['activities']['reaction']['materials']
                mat_insert = [(i, m['typeID'], m['quantity']) for m in materials]

                c.execute('INSERT INTO blueprints VALUES(?,?,?);', (i, product['typeID'], product['quantity']))
                c.executemany('INSERT INTO blueprint_materials VALUES(?,?,?);', mat_insert)

            elif "manufacturing" in blu['activities'] and 'materials' in blu['activities']['manufacturing'] and 'products' in blu['activities']['manufacturing']:
                product = blu['activities']['manufacturing']['products'][0]
                materials = blu['activities']['manufacturing']['materials']
                mat_insert = [(i, m['typeID'], m['quantity']) for m in materials]

                c.execute('INSERT INTO blueprints VALUES(?,?,?);', (i, product['typeID'], product['quantity']))
                c.executemany('INSERT INTO blueprint_materials VALUES(?,?,?);', mat_insert)

        con.commit()


if __name__ == '__main__':
    db_name = "eve.db"
    connection = sqlite3.connect(db_name)
    create_tables(connection)
    load_groups(connection)
    load_types(connection)
    load_blueprints(connection)
    fetch_all_prices(db_name).join()
