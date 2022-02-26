import os
import redis
from flask import Flask
from optiplex.composite_optimizer import CompositeOptimizer
from flask_session import Session


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE=os.path.join(app.instance_path, 'eve.sqlite'),
        SESSION_TYPE='redis',
        SESSION_PERMANENT=True,
        SESSION_USE_SIGNER=True,
        SESSION_REDIS=redis.Redis(host=os.environ.get("REDIS_HOST"), port=6379)
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)


    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    from . import database
    database.init_app(app)

    # setup session redis db
    Session(app)

    from . import production
    app.register_blueprint(production.bp)

    from . import reactions
    app.register_blueprint(reactions.bp)

    from . import esi
    with app.app_context():
        try:
            esi.fetch_adjust_price(database.get_db())
        except:
            pass

    return app