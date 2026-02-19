# routes/__init__.py
from flask import Blueprint, render_template

# Create a main blueprint for general routes
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/map')
def map_view():
    return render_template('map.html')
@main_bp.route('/favicon.ico')
def favicon():
    return '', 204  # Return empty response with 204 No Content

@main_bp.route('/test')
def test():
    return "<h1>Test Page Works!</h1><p>If you can see this, Flask is rendering properly.</p>"
# Export the blueprint
__all__ = ['main_bp']
# Add this to routes/__init__.py after the existing routes

