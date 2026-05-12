# coding: utf-8
"""
文档数据模型

定义知识库相关的数据表结构
"""

from datetime import datetime
from peewee import Model, CharField, TextField, DateTimeField, IntegerField, ForeignKeyField, BooleanField

from app.utils.db_utils import db_manager


class Document(Model):
    """文档表"""
    
    id = IntegerField(primary_key=True)
    title = CharField(max_length=255, verbose_name="文档标题")
    content = TextField(verbose_name="文档内容")
    file_path = CharField(max_length=512, verbose_name="文件路径")
    file_type = CharField(max_length=50, verbose_name="文件类型")
    file_size = IntegerField(verbose_name="文件大小(字节)")
    file_hash = CharField(max_length=64, unique=True, verbose_name="文件哈希")
    chunk_count = IntegerField(default=0, verbose_name="分块数量")
    vector_store_id = CharField(max_length=255, verbose_name="向量存储ID")
    metadata = TextField(default='{}', verbose_name="元数据")
    is_active = BooleanField(default=True, verbose_name="是否激活")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    class Meta:
        database = db_manager.get('zj3')
        table_name = 'documents'
        indexes = (
            (('file_hash',), True),
            (('vector_store_id',), False),
            (('is_active',), False),
        )


class DocumentCollection(Model):
    """文档集合表（用于组织不同类型的知识库）"""
    
    id = IntegerField(primary_key=True)
    name = CharField(max_length=100, unique=True, verbose_name="集合名称")
    description = TextField(verbose_name="集合描述")
    department = CharField(max_length=100, verbose_name="所属部门")
    is_public = BooleanField(default=False, verbose_name="是否公开")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    class Meta:
        database = db_manager.get('zj3')
        table_name = 'document_collections'


class ChatSession(Model):
    """聊天会话表"""
    
    id = IntegerField(primary_key=True)
    session_id = CharField(max_length=100, unique=True, verbose_name="会话ID")
    user_id = CharField(max_length=100, verbose_name="用户ID")
    agent_type = CharField(max_length=50, verbose_name="智能体类型")
    title = CharField(max_length=255, verbose_name="会话标题")
    status = CharField(max_length=20, default='active', verbose_name="状态")
    metadata = TextField(default='{}', verbose_name="元数据")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    class Meta:
        database = db_manager.get('zj3')
        table_name = 'chat_sessions'
        indexes = (
            (('session_id',), True),
            (('user_id',), False),
            (('agent_type',), False),
        )


class ChatMessage(Model):
    """聊天消息表"""
    
    id = IntegerField(primary_key=True)
    session_id = ForeignKeyField(ChatSession, backref='messages', verbose_name="会话ID")
    role = CharField(max_length=20, verbose_name="角色(user/assistant/system)")
    content = TextField(verbose_name="消息内容")
    tokens_used = IntegerField(default=0, verbose_name="使用的Token数")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    
    class Meta:
        database = db_manager.get('zj3')
        table_name = 'chat_messages'
        indexes = (
            (('session_id',), False),
            (('created_at',), False),
        )


class WorkflowTask(Model):
    """工作流任务表"""
    
    id = IntegerField(primary_key=True)
    task_id = CharField(max_length=100, unique=True, verbose_name="任务ID")
    task_type = CharField(max_length=50, verbose_name="任务类型")
    status = CharField(max_length=20, default='pending', verbose_name="状态")
    input_data = TextField(verbose_name="输入数据")
    output_data = TextField(verbose_name="输出数据")
    error_message = TextField(verbose_name="错误信息")
    priority = IntegerField(default=5, verbose_name="优先级(1-10)")
    retry_count = IntegerField(default=0, verbose_name="重试次数")
    created_by = CharField(max_length=100, verbose_name="创建者")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    completed_at = DateTimeField(null=True, verbose_name="完成时间")
    
    class Meta:
        database = db_manager.get('zj3')
        table_name = 'workflow_tasks'
        indexes = (
            (('task_id',), True),
            (('task_type',), False),
            (('status',), False),
            (('priority',), False),
        )


class UserPermission(Model):
    """用户权限表"""
    
    id = IntegerField(primary_key=True)
    user_id = CharField(max_length=100, verbose_name="用户ID")
    role = CharField(max_length=50, verbose_name="角色")
    agent_types = TextField(default='[]', verbose_name="可访问的智能体类型")
    permissions = TextField(default='[]', verbose_name="权限列表")
    data_scope = CharField(max_length=50, default='self', verbose_name="数据范围")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    class Meta:
        database = db_manager.get('zj3')
        table_name = 'user_permissions'
        indexes = (
            (('user_id',), True),
            (('role',), False),
        )


def create_tables():
    """创建所有表"""
    tables = [
        Document,
        DocumentCollection,
        ChatSession,
        ChatMessage,
        WorkflowTask,
        UserPermission
    ]
    
    db = db_manager.get('zj3')
    db.create_tables(tables, safe=True)
    print("数据表创建完成")


if __name__ == "__main__":
    create_tables()