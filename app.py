from flask import Flask, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from config import Config
from models import db, Users


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
