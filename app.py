from flask import Flask, render_template

from config import Config
from initialize_db import initialize_database
from views.auth_view import auth_bp
from views.calendar_view import calendar_bp
from views.export_view import export_bp
from views.category_view import category_bp
from views.user_view import user_bp


def create_app():
    """
    Application Factory.

    Responsável exclusivamente pela criação e configuração
    da aplicação Flask e pelo registro dos Blueprints.
    """

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )

    # Configurações da aplicação
    app.config.from_object(Config)

    # Registro dos Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(user_bp)

    # Rota principal
    @app.route("/")
    def index():
        return render_template("index.html")

    return app

app = create_app()

if __name__ == "__main__":
    try:
        initialize_database()

    except Exception as error:
        print(f"Erro ao inicializar banco de dados: {error}")
        raise
    app.run(debug=True)
