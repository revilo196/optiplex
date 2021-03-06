import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext

from .import_static import load_groups, load_types, load_blueprints, load_icons
from .esi import fetch_reactions_prices


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


# create tables and load static data into table
def init_db():
    db = get_db()

    with current_app.open_resource('create_tables.sql') as f:
        db.executescript(f.read().decode('utf8'))

    load_groups(db)
    load_icons(db)
    load_types(db)
    load_blueprints(db)
    fetch_reactions_prices(db)


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')
