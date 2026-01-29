from flask import Blueprint

redactor_bp = Blueprint("redactor", __name__, url_prefix="/redactor")

from . import routes
