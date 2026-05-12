from flask import Blueprint, jsonify, request

from app.services.basic_service import BasicSvr
from app.views import LoginRequiredDispatchView
from app._webapi import *

basic_app = Blueprint('basic', __name__)


class Basic(LoginRequiredDispatchView):
    @rpc(
        '添加账号',
        args=dict(
            securityCode=required.StringField(desc='安全码'),
            cardNumber=required.StringField(desc='安全码'),
            month=required.IntegerField(desc='月'),
            year=required.StringField(desc='年'),
        ),
        returns=dict(

    ))
    def add_account(self, req, rsp):
        svr = BasicSvr()
        svr.add_account(req)
        rsp.data = rsp.new()
