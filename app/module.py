# coding=u8

import os.path as osp
from flask import Blueprint, url_for, request, get_flashed_messages, g
import config

module = Blueprint(config.APP_NAME, __name__)

# 若普通api
from .views import *
