import peewee

# 定义一个用户表模型
from app.models import BaseModel, db


class Account(BaseModel):
    securityCode = peewee.CharField()
    cardNumber = peewee.CharField()
    month = peewee.CharField()
    year = peewee.CharField()
    postalCode = peewee.CharField()

    class Meta:
        db_table = 'account'

if not Account.table_exists():
    Account.create_table()