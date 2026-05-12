from flask import Blueprint, jsonify, request

from app.services.basic_service import BasicSvr
from app.views import LoginRequiredDispatchView
from app._webapi import *

basic_app = Blueprint('basic', __name__)


class Mcp(LoginRequiredDispatchView):
    ''''''
