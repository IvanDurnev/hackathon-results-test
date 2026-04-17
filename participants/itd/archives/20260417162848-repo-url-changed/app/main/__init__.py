from flask import Blueprint

bp = Blueprint('main', __name__)
# sub = Blueprint('sub', __name__, subdomain='<city>')

from app.main import routes
