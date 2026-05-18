"""注册所有 Blueprint"""
from routes.auth import auth_bp
from routes.protocol import protocol_bp
from routes.calculator import calc_bp
from routes.ai import ai_bp
from routes.instrument import instrument_bp
from routes.journal import journal_bp
from routes.admin import admin_bp
from routes.export import export_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(protocol_bp)
    app.register_blueprint(calc_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(instrument_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(export_bp)
