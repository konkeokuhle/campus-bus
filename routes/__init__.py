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
    return '', 204

# Export the blueprint
__all__ = ['main_bp']
