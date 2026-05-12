import datetime

from app.models.basic_model import Account as AccountModel
from app.services.common_help_services import HelperSvcApi


class BasicSvr(HelperSvcApi):
    def add_account(self, req):
        result = 0
        message = 'success'
        now = datetime.datetime.now()
        item = {
            'securityCode': req.get('securityCode'),
            'cardNumber': req.get('cardNumber'),
            'month': req.get('month'),
            'year': req.get('year'),
            'postalCode': req.get('postalCode'),
            'create_at': now,
            'update_at': now,
        }
        try:
            AccountModel.insert(item).execute()
        except:
            raise Exception('参数错误')

        return result, message
