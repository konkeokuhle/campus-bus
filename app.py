# app.py
from flask import Flask, render_template
from flask_mysqldb import MySQL
from flask_socketio import SocketIO
from flask_session import Session
import os
from datetime import datetime
from config import Config

# Initialize extensions
mysql = MySQL()
socketio = SocketIO(cors_allowed_origins="*")
session = Session()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # CRITICAL: Ensure secret key is set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'emergency-fallback-key-123!@#$%'
        print("⚠️  WARNING: Using emergency fallback secret key!")
    
    # Print debug info
    print("=" * 50)
    print("APP CONFIGURATION:")
    print(f"SECRET_KEY set: {'YES' if app.config.get('SECRET_KEY') else 'NO'}")
    if app.config.get('SECRET_KEY'):
        print(f"SECRET_KEY (first 10 chars): {app.config['SECRET_KEY'][:10]}...")
    print(f"SESSION_TYPE: {app.config.get('SESSION_TYPE', 'Not set')}")
    print(f"Database: {app.config.get('MYSQL_USER')}@{app.config.get('MYSQL_HOST')}/{app.config.get('MYSQL_DB')}")
    print("=" * 50)
    
    # Initialize extensions with app
    mysql.init_app(app)
    socketio.init_app(app)
    session.init_app(app)
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.driver import driver_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    from routes import main_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(driver_bp, url_prefix='/driver')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(main_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register context processors
    register_context_processors(app)
    
    return app

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

def register_context_processors(app):
    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.utcnow,
            'app_name': 'Campus Bus'
        }

# For running directly
if __name__ == '__main__':
    app = create_app()
    if app:
        print("✅ App created successfully!")
        socketio.run(app, debug=True)
    else:
        print("❌ Failed to create app!")