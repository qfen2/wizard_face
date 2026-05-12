# coding: utf-8
"""
安全与权限控制服务

提供基于角色的访问控制、API鉴权、数据脱敏等功能
"""

import hashlib
import hmac
import uuid
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from functools import wraps
import json
import re

from app.models.document_model import UserPermission
from app.utils.db_utils import db_manager


# ==================== 角色定义 ====================
class Role:
    """角色定义"""
    ADMIN = "admin"  # 管理员
    MANAGER = "manager"  # 经理
    EMPLOYEE = "employee"  # 员工
    GUEST = "guest"  # 访客
    
    # 角色层级（数字越大权限越高）
    ROLE_LEVEL = {
        GUEST: 1,
        EMPLOYEE: 2,
        MANAGER: 3,
        ADMIN: 4
    }


# ==================== 权限定义 ====================
class Permission:
    """权限定义"""
    # 智能体访问权限
    ACCESS_CUSTOMER_SERVICE = "access_customer_service"
    ACCESS_APPROVAL = "access_approval"
    ACCESS_DATA_ANALYSIS = "access_data_analysis"
    ACCESS_RESEARCH_ASSISTANT = "access_research_assistant"
    
    # 知识库权限
    VIEW_KNOWLEDGE_BASE = "view_knowledge_base"
    UPLOAD_DOCUMENT = "upload_document"
    DELETE_DOCUMENT = "delete_document"
    MANAGE_COLLECTION = "manage_collection"
    
    # 数据权限
    VIEW_ALL_DATA = "view_all_data"
    VIEW_DEPARTMENT_DATA = "view_department_data"
    VIEW_OWN_DATA = "view_own_data"
    EXPORT_DATA = "export_data"
    
    # 系统权限
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_LOGS = "view_logs"
    SYSTEM_CONFIG = "system_config"


# ==================== API 鉴权管理器 ====================
class AuthManager:
    """API鉴权管理器"""
    
    def __init__(self):
        """初始化鉴权管理器"""
        self.secret_key = self._get_secret_key()
        self._tokens = {}  # 内存中的token缓存
    
    def _get_secret_key(self) -> str:
        """获取密钥"""
        # 从配置或环境变量获取
        import os
        return os.getenv('AUTH_SECRET_KEY', 'default_secret_key_change_in_production')
    
    def generate_token(self, user_id: str, expires_in: int = 3600) -> str:
        """
        生成访问令牌
        
        Args:
            user_id: 用户ID
            expires_in: 过期时间（秒）
            
        Returns:
            令牌字符串
        """
        expiry = datetime.now() + timedelta(seconds=expires_in)
        token_data = {
            'user_id': user_id,
            'expires_at': expiry.isoformat(),
            'nonce': str(uuid.uuid4())
        }
        
        # 简单的token生成（生产环境应使用JWT）
        token_str = json.dumps(token_data, sort_keys=True)
        signature = hmac.new(
            self.secret_key.encode(),
            token_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{token_str}.{signature}"
        
        # 缓存token
        self._tokens[token] = token_data
        
        return token
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        验证令牌
        
        Args:
            token: 令牌字符串
            
        Returns:
            令牌数据字典，验证失败返回None
        """
        try:
            # 检查缓存
            if token not in self._tokens:
                return None
            
            token_data = self._tokens[token]
            
            # 检查过期
            expiry = datetime.fromisoformat(token_data['expires_at'])
            if datetime.now() > expiry:
                del self._tokens[token]
                return None
            
            return token_data
        except Exception as e:
            print(f"令牌验证失败: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """
        撤销令牌
        
        Args:
            token: 令牌字符串
            
        Returns:
            是否撤销成功
        """
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False


# ==================== 权限管理器 ====================
class PermissionManager:
    """权限管理器"""
    
    # 角色权限映射
    ROLE_PERMISSIONS = {
        Role.ADMIN: [
            Permission.ACCESS_CUSTOMER_SERVICE,
            Permission.ACCESS_APPROVAL,
            Permission.ACCESS_DATA_ANALYSIS,
            Permission.ACCESS_RESEARCH_ASSISTANT,
            Permission.VIEW_KNOWLEDGE_BASE,
            Permission.UPLOAD_DOCUMENT,
            Permission.DELETE_DOCUMENT,
            Permission.MANAGE_COLLECTION,
            Permission.VIEW_ALL_DATA,
            Permission.VIEW_DEPARTMENT_DATA,
            Permission.VIEW_OWN_DATA,
            Permission.EXPORT_DATA,
            Permission.MANAGE_USERS,
            Permission.MANAGE_ROLES,
            Permission.VIEW_LOGS,
            Permission.SYSTEM_CONFIG
        ],
        Role.MANAGER: [
            Permission.ACCESS_CUSTOMER_SERVICE,
            Permission.ACCESS_APPROVAL,
            Permission.ACCESS_DATA_ANALYSIS,
            Permission.ACCESS_RESEARCH_ASSISTANT,
            Permission.VIEW_KNOWLEDGE_BASE,
            Permission.UPLOAD_DOCUMENT,
            Permission.VIEW_DEPARTMENT_DATA,
            Permission.VIEW_OWN_DATA,
            Permission.EXPORT_DATA
        ],
        Role.EMPLOYEE: [
            Permission.ACCESS_CUSTOMER_SERVICE,
            Permission.ACCESS_DATA_ANALYSIS,
            Permission.VIEW_KNOWLEDGE_BASE,
            Permission.VIEW_OWN_DATA
        ],
        Role.GUEST: [
            Permission.ACCESS_CUSTOMER_SERVICE,
            Permission.VIEW_KNOWLEDGE_BASE
        ]
    }
    
    def __init__(self):
        """初始化权限管理器"""
        self.db = db_manager.get('zj3')
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """
        获取用户权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            权限集合
        """
        try:
            user_perm = UserPermission.get(UserPermission.user_id == user_id)
            
            # 获取角色权限
            role_perms = set(self.ROLE_PERMISSIONS.get(user_perm.role, []))
            
            # 获取自定义权限
            custom_perms = set(json.loads(user_perm.permissions))
            
            # 合并权限
            return role_perms | custom_perms
        except UserPermission.DoesNotExist:
            # 默认返回访客权限
            return set(self.ROLE_PERMISSIONS.get(Role.GUEST, []))
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """
        检查用户是否有指定权限
        
        Args:
            user_id: 用户ID
            permission: 权限名称
            
        Returns:
            是否有权限
        """
        permissions = self.get_user_permissions(user_id)
        return permission in permissions
    
    def check_data_scope(self, user_id: str, data_owner_id: str = None, department: str = None) -> bool:
        """
        检查数据访问范围
        
        Args:
            user_id: 用户ID
            data_owner_id: 数据所有者ID
            department: 部门
            
        Returns:
            是否可以访问
        """
        try:
            user_perm = UserPermission.get(UserPermission.user_id == user_id)
            data_scope = user_perm.data_scope
            
            if data_scope == 'all':
                return True
            elif data_scope == 'department':
                # 检查部门权限（简化处理）
                return True
            elif data_scope == 'self':
                # 只能访问自己的数据
                return data_owner_id == user_id
            
            return False
        except UserPermission.DoesNotExist:
            return False
    
    def assign_role(self, user_id: str, role: str) -> bool:
        """
        分配角色给用户
        
        Args:
            user_id: 用户ID
            role: 角色名称
            
        Returns:
            是否分配成功
        """
        try:
            user_perm, created = UserPermission.get_or_create(
                user_id=user_id,
                defaults={
                    'role': role,
                    'agent_types': '[]',
                    'permissions': '[]',
                    'data_scope': 'self'
                }
            )
            
            if not created:
                user_perm.role = role
                user_perm.updated_at = datetime.now()
                user_perm.save()
            
            return True
        except Exception as e:
            print(f"分配角色失败: {e}")
            return False


# ==================== 数据脱敏器 ====================
class DataMasker:
    """数据脱敏器"""
    
    # 敏感字段模式
    PATTERNS = {
        'phone': r'1[3-9]\d{9}',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'id_card': r'\d{17}[\dXx]',
        'credit_card': r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
        'bank_account': r'\d{16,19}'
    }
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """
        脱敏手机号
        
        Args:
            phone: 手机号
            
        Returns:
            脱敏后的手机号
        """
        if len(phone) == 11:
            return phone[:3] + '****' + phone[7:]
        return phone
    
    @staticmethod
    def mask_email(email: str) -> str:
        """
        脱敏邮箱
        
        Args:
            email: 邮箱地址
            
        Returns:
            脱敏后的邮箱
        """
        if '@' in email:
            parts = email.split('@')
            username = parts[0]
            if len(username) > 3:
                username = username[:2] + '***'
            return username + '@' + parts[1]
        return email
    
    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """
        脱敏身份证号
        
        Args:
            id_card: 身份证号
            
        Returns:
            脱敏后的身份证号
        """
        if len(id_card) >= 15:
            return id_card[:6] + '********' + id_card[-4:]
        return id_card
    
    @staticmethod
    def mask_credit_card(card: str) -> str:
        """
        脱敏信用卡号
        
        Args:
            card: 信用卡号
            
        Returns:
            脱敏后的信用卡号
        """
        # 移除空格和横线
        clean_card = re.sub(r'[-\s]', '', card)
        if len(clean_card) == 16:
            return clean_card[:4] + '********' + clean_card[-4:]
        return card
    
    @staticmethod
    def mask_name(name: str) -> str:
        """
        脱敏姓名
        
        Args:
            name: 姓名
            
        Returns:
            脱敏后的姓名
        """
        if len(name) > 1:
            return name[0] + '*' * (len(name) - 1)
        return name
    
    @classmethod
    def mask_data(cls, data: Any, fields_to_mask: List[str] = None) -> Any:
        """
        脱敏数据
        
        Args:
            data: 数据（字典或字符串）
            fields_to_mask: 需要脱敏的字段列表
            
        Returns:
            脱敏后的数据
        """
        if fields_to_mask is None:
            fields_to_mask = ['phone', 'email', 'id_card', 'credit_card', 'name']
        
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if key in fields_to_mask:
                    if key == 'phone':
                        masked_data[key] = cls.mask_phone(str(value))
                    elif key == 'email':
                        masked_data[key] = cls.mask_email(str(value))
                    elif key == 'id_card':
                        masked_data[key] = cls.mask_id_card(str(value))
                    elif key == 'credit_card':
                        masked_data[key] = cls.mask_credit_card(str(value))
                    elif key == 'name':
                        masked_data[key] = cls.mask_name(str(value))
                    else:
                        masked_data[key] = value
                else:
                    masked_data[key] = value
            return masked_data
        elif isinstance(data, str):
            # 自动识别并脱敏敏感信息
            masked = data
            for pattern in cls.PATTERNS.values():
                matches = re.finditer(pattern, masked)
                for match in matches:
                    matched_text = match.group()
                    if '@' in matched_text:
                        masked = masked.replace(matched_text, cls.mask_email(matched_text))
                    elif len(matched_text) == 11:
                        masked = masked.replace(matched_text, cls.mask_phone(matched_text))
            return masked
        else:
            return data


# ==================== 装饰器 ====================
def require_permission(permission: str):
    """
    权限检查装饰器
    
    Args:
        permission: 需要的权限
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从kwargs中获取user_id
            user_id = kwargs.get('user_id')
            
            if not user_id:
                raise PermissionError("缺少用户ID")
            
            perm_manager = PermissionManager()
            if not perm_manager.has_permission(user_id, permission):
                raise PermissionError(f"用户没有权限: {permission}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_auth():
    """
    认证检查装饰器
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从kwargs中获取token
            token = kwargs.get('token')
            
            if not token:
                raise PermissionError("缺少访问令牌")
            
            auth_manager = AuthManager()
            token_data = auth_manager.validate_token(token)
            
            if not token_data:
                raise PermissionError("无效或过期的令牌")
            
            # 将user_id添加到kwargs
            kwargs['user_id'] = token_data['user_id']
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== 安全服务主类 ====================
class SecurityService:
    """安全服务主类"""
    
    def __init__(self):
        """初始化安全服务"""
        self.auth_manager = AuthManager()
        self.permission_manager = PermissionManager()
        self.data_masker = DataMasker()
    
    def login(self, user_id: str, password: str) -> Dict[str, Any]:
        """
        用户登录
        
        Args:
            user_id: 用户ID
            password: 密码
            
        Returns:
            登录结果
        """
        # 这里应该验证密码，简化处理直接生成token
        token = self.auth_manager.generate_token(user_id)
        
        # 获取用户信息
        try:
            user_perm = UserPermission.get(UserPermission.user_id == user_id)
            role = user_perm.role
        except UserPermission.DoesNotExist:
            role = Role.GUEST
        
        return {
            'success': True,
            'token': token,
            'user_id': user_id,
            'role': role,
            'expires_in': 3600
        }
    
    def logout(self, token: str) -> Dict[str, Any]:
        """
        用户登出
        
        Args:
            token: 访问令牌
            
        Returns:
            登出结果
        """
        revoked = self.auth_manager.revoke_token(token)
        return {
            'success': revoked,
            'message': '登出成功' if revoked else '令牌无效'
        }
    
    def check_access(
        self,
        token: str,
        permission: str
    ) -> Dict[str, Any]:
        """
        检查访问权限
        
        Args:
            token: 访问令牌
            permission: 权限名称
            
        Returns:
            检查结果
        """
        token_data = self.auth_manager.validate_token(token)
        
        if not token_data:
            return {
                'success': False,
                'message': '无效或过期的令牌'
            }
        
        user_id = token_data['user_id']
        has_perm = self.permission_manager.has_permission(user_id, permission)
        
        return {
            'success': has_perm,
            'user_id': user_id,
            'permission': permission,
            'message': '有权限' if has_perm else '无权限'
        }
    
    def mask_sensitive_data(
        self,
        data: Any,
        user_id: str = None,
        fields: List[str] = None
    ) -> Any:
        """
        脱敏敏感数据
        
        Args:
            data: 原始数据
            user_id: 用户ID（用于检查权限）
            fields: 需要脱敏的字段
            
        Returns:
            脱敏后的数据
        """
        # 如果没有提供fields，使用默认的敏感字段
        if fields is None:
            fields = ['phone', 'email', 'id_card', 'credit_card', 'name']
        
        return self.data_masker.mask_data(data, fields)


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 创建安全服务
    security = SecurityService()
    
    print("=" * 60)
    print("安全与权限控制示例")
    print("=" * 60)
    
    # 1. 用户登录
    print("\n1. 用户登录")
    login_result = security.login("user123", "password123")
    print(f"登录结果: {login_result['success']}")
    print(f"令牌: {login_result['token'][:20]}...")
    print(f"角色: {login_result['role']}")
    
    token = login_result['token']
    
    # 2. 检查权限
    print("\n2. 检查权限")
    access_result = security.check_access(token, Permission.ACCESS_CUSTOMER_SERVICE)
    print(f"访问客服智能体: {access_result['success']}")
    
    access_result = security.check_access(token, Permission.MANAGE_USERS)
    print(f"管理用户: {access_result['success']}")
    
    # 3. 数据脱敏
    print("\n3. 数据脱敏")
    sensitive_data = {
        'name': '张三',
        'phone': '13800138000',
        'email': 'zhangsan@example.com',
        'id_card': '110101199001011234',
        'address': '北京市朝阳区',
        'age': 30
    }
    
    print("原始数据:")
    print(json.dumps(sensitive_data, ensure_ascii=False, indent=2))
    
    masked_data = security.mask_sensitive_data(sensitive_data)
    print("\n脱敏后数据:")
    print(json.dumps(masked_data, ensure_ascii=False, indent=2))
    
    # 4. 使用装饰器
    print("\n4. 使用装饰器")
    
    @require_auth()
    @require_permission(Permission.ACCESS_DATA_ANALYSIS)
    def analyze_data(user_id: str, data: dict):
        return f"用户 {user_id} 正在分析数据"
    
    try:
        result = analyze_data(token=token, data={'test': 'data'})
        print(f"分析结果: {result}")
    except PermissionError as e:
        print(f"权限错误: {e}")
    
    # 5. 用户登出
    print("\n5. 用户登出")
    logout_result = security.logout(token)
    print(f"登出结果: {logout_result['message']}")
    
    # 6. 验证登出后的token
    print("\n6. 验证登出后的token")
    access_result = security.check_access(token, Permission.ACCESS_CUSTOMER_SERVICE)
    print(f"访问权限: {access_result['success']}")
    print(f"消息: {access_result['message']}")