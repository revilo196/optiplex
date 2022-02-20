import sqlite3
import yaml
from pathlib import Path

import_path = "import/sde/fsd/"


def create_tables(con: sqlite3.Connection):
    c = con.cursor()
    with open("create_tables.sql") as f:
        print("creating tables")
        c.executescript(f.read())


def load_groups(con: sqlite3.Connection):
    c = con.cursor()
    with open(import_path + 'groupIDs.yaml', 'r') as file:
        print("groupIDs -- file_opened -- starting reading")
        groups_db = yaml.load(file, Loader=yaml.CLoader)
        print("done loading")
        groups = [(i, group['name']['en']) for (i, group) in groups_db.items() if 'en' in group['name']]
        print("inserting to DB")
        c.executemany('INSERT INTO groupIDs VALUES(?,?);', groups)
        con.commit()


def load_icons(con: sqlite3.Connection):
    c = con.cursor()
    with open(import_path + 'iconIDs.yaml', 'r') as file:
        print("icons -- file_opened -- starting reading")
        icons_db = yaml.load(file, Loader=yaml.CLoader)
        print("done loading")
        icons = [(i, Path(group['iconFile']).name) for (i, group) in icons_db.items()]
        print("inserting to DB")
        c.executemany('INSERT INTO icons VALUES(?,?);', icons)


def load_graphics(con: sqlite3.Connection):
    c = con.cursor()
    with open(import_path + 'iconIDs.yaml', 'r') as file:
        print("icons -- file_opened -- starting reading")
        icons_db = yaml.load(file, Loader=yaml.CLoader)
        print("done loading")
        icons = [(i, Path(group['iconFile']).name) for (i, group) in icons_db.items()]
        print("inserting to DB")
        c.executemany('INSERT INTO icons VALUES(?,?);', icons)


def load_types(con):
    c = con.cursor()
    with open(import_path + 'typeIDs.yaml', 'r') as file:
        print("types -- file_opened -- starting reading")
        types_db = yaml.load(file, Loader=yaml.CLoader)
        print("done loading")
        types = [(i, ty['name']['en'], ty['groupID']) for (i, ty) in types_db.items() if 'en' in ty['name']]
        icons = [(ty['iconID'], i) for (i, ty) in types_db.items() if 'iconID' in ty]
        graphics = [(ty['graphicID'], i) for (i, ty) in types_db.items() if 'graphicID' in ty]

        print("inserting to DB")
        c.executemany('INSERT INTO typeIDs (id, name, group_id)  VALUES(?,?,?);', types)
        c.executemany('UPDATE typeIDs SET iconID = ?  WHERE typeIDs.id = ?', icons)
        c.executemany('UPDATE typeIDs SET graphicID = ?  WHERE typeIDs.id = ?', graphics)
        con.commit()


def load_blueprints(con):
    c = con.cursor()
    with open(import_path  + 'blueprints.yaml', 'r') as file:
        print("blueprints -- file_opened -- starting reading")
        blueprints = yaml.load(file, Loader=yaml.CLoader)

        print("inserting to DB")
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
