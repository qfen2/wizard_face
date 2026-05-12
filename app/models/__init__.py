import peewee

# 配置数据库连接
db = peewee.MySQLDatabase('wz', user='root', password='wiseyq123', host='localhost', port=3306)

# 定义模型
class BaseModel(peewee.Model):
    id = peewee.PrimaryKeyField()
    create_at = peewee.DateTimeField()
    update_at = peewee.DateTimeField()
    delete_at = peewee.DateTimeField(null=True)

    class Meta:
        database = db
