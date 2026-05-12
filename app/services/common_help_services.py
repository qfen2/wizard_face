import datetime
import logging
import os

from app.consts.errors import Error
from config import ZJ_BASE_DIR

logger = logging.getLogger(__name__)

class BaseSvc(object):
    pass


class HelperSvcApi(BaseSvc):
    def __init__(self):
        pass

    @staticmethod
    def create_obj(model, req):
        now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        obj_dic = req.__dict__['_field_values']
        obj_dic.update({
            'create_at': now_time,
            'update_at': now_time,
        })

        for k, v in obj_dic.items():
            if v:
                setattr(model, k, v)
        return model

    @staticmethod
    def update_obj(model, req):
        now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        obj_dic = req.__dict__['_field_values']
        obj_dic.update({
            'update_at': now_time,
        })

        for k, v in obj_dic.items():
            if v is not None:
                setattr(model, k, v)

        return model

    @staticmethod
    def get_base_cond(obj, req):
        cond = (obj.group_id == req.group_id)
        if req.team_id:
            cond = cond & (obj.team_id == req.team_id)
        if req.project_id:
            cond = cond & (obj.project_id == req.project_id)

        return cond

    def check_name_repeat(self, model, req, _field, name, _id=None):
        cond = self.get_base_cond(model, req)
        if _id:
            cond = cond & (model.id!=_id)
        cond = cond & (getattr(model, _field)==name)
        issue = model.select().where(cond).no_deleted().get_or_none()
        if issue:
            return True

        return False

    def datetime_to_str(self, date_time, format='%Y-%m-%d'):
        if date_time:
            return date_time.strftime(format)
        else:
            return ''

    def _model_db_create(self, model=None, req=None, user_id=None, **kwargs) -> (int, list):
        if not req.name:
            raise Error.clsf(-9999, '未定义错误')

        total = 0
        items = list()

        base_cond = self.get_base_cond(model, req)

        cond = base_cond & (model.name == req.name)

        check_name = model.select().where(cond).no_deleted().get_or_none()
        if check_name:
            raise CommonErrors.NameRepeatError
        item = model()
        item = self.create_obj(item, req)
        if getattr(model, 'sender', None):
            item.sender = user_id

        try:
            item.save()
        except:
            raise CommonErrors.CreateError

        return total, items

    def _model_db_list(self, model=None, req=None, **kwargs) -> (int, list):
        cond = self.get_base_cond(model, req)
        if req.kw:
            cond = cond & (model.name.contains(req.kw))
        items = model.select().where(cond).paginate(
            req.page, req.pageSize).no_deleted()
        total = model.select().where(cond).no_deleted().count()

        for item in items:
            item.create_at = self.datetime_to_str(item.create_at)

        return total, items

    def _model_db_update(self, model=None, typ_id=None, req=None, user_id=None, **kwargs) -> (int, list):
        if not typ_id:
            raise CommonErrors.ArgsError

        total = 0
        items = list()

        base_cond = self.get_base_cond(model, req)
        cond = base_cond & (model.id != typ_id) & (
                model.name == req.name)

        check_name = model.select().where(cond).no_deleted().get_or_none()
        if check_name:
            raise CommonErrors.NameRepeatError

        item = model.select().where(base_cond & (
                model.id == typ_id)).no_deleted().get_or_none()

        item = self.update_obj(item, req)
        if getattr(model, 'sender'):
            item.sender = user_id

        item.save()

        return total, items

    def _model_db_del(self, model=None, typ_id=None, req=None, **kwargs) -> (int, list):
        if not typ_id:
            raise CommonErrors.ArgsError
        total = 0
        items = list()

        # 删除流程类型前判断是否有审批流程引用
        delete_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        base_cond = self.get_base_cond(model, req)
        cond = base_cond & (model.id == typ_id)
        model.update(delete_at=delete_at).where(cond).execute()

        return total, items

    def operate_model(self, **kwargs) -> (int, list):
        op_typ = kwargs.get('req').op_typ

        _op_method = getattr(self, model_type_map.get(op_typ))

        total, items = _op_method(**kwargs)

        return total, items
