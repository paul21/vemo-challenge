"""
Carbon Snapshot Console - Aplicacion Flask

Arquitectura:
- Patron Application Factory para facilitar testing y configuracion
- Blueprints separados: API interna, API publica, Backoffice HTML, Recibos PDF
- Servicios desacoplados para calculo de carbono y envio de emails
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()

# Extensiones inicializadas sin app (patron factory)
db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
migrate = Migrate()
cors = CORS()

def setup_logging(app):
    """Configure logging for the application"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'vemo.log')

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else 'logs'
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging format
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_level))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Configure Flask app logger
    app.logger.setLevel(getattr(logging, log_level))

    # Log application startup
    app.logger.info("Vemo application logging initialized")

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///carbon_console.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-production')

    # Email configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'localhost')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@carbonconsole.com')

    # Celery configuration
    app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    app.config['CELERY_RESULT_BACKEND'] = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    # Setup logging
    setup_logging(app)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/*": {"origins": "*"}})

    # Blueprints importados dentro de create_app para evitar imports circulares
    from routes.internal_api import internal_api
    from routes.public_api import public_api
    from routes.receipts import receipts
    from routes.backoffice import backoffice

    app.register_blueprint(internal_api, url_prefix='/api')      # API para usuarios internos (backoffice)
    app.register_blueprint(public_api, url_prefix='/public')     # API para usuarios externos
    app.register_blueprint(receipts)                              # Generacion de PDFs
    app.register_blueprint(backoffice, url_prefix='/bo')         # UI HTML del backoffice

    app.logger.info("Vemo application created successfully")
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, use_reloader=False)
