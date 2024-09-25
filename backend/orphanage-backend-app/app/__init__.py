from flask import Flask # type: ignore
from app.config import Config
from app.orphan_routes import orphans
from app.auth_routes import auth
from app.donations_routes import donations
from app.homepage_routes import homePage
from app.admin_routes import admin

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Register the Blueprint from routes
    # app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(orphans)
    app.register_blueprint(donations)
    app.register_blueprint(homePage)
    app.register_blueprint(admin)

    return app