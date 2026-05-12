from functools import wraps
from flask import request, jsonify
from enum import Enum


class InputType(Enum):
    FORM = 'form'
    JSON = 'json'


def rpc(desc, args=None, returns=None, input_type=InputType.FORM):
    """
    RPC装饰器，用于处理请求参数验证和响应格式化

    Args:
        descr: API描述
        args: 参数定义字典
        returns: 返回值定义
        input_type: 输入类型(FORM/JSON)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *f_args, **f_kwargs):
            # 创建请求和响应对象
            req = RequestObject()
            rsp = ResponseObject()
            try:
                # 根据 input_type 获取请求数据
                if input_type == InputType.JSON:
                    raw_data = request.get_json(silent=True) or {}
                else:
                    # 优先取 querystring，再合并 form，确保 GET 也能取到参数
                    raw_data = {}
                    raw_data.update(request.args.to_dict())
                    raw_data.update(request.form.to_dict())

                # 验证并解析输入参数
                validated_data = validate_input(raw_data, args)
                req.update(validated_data)

                # 调用实际的处理函数
                func(self, req, rsp)

                # 验证返回值格式
                if returns:
                    rsp.data = validate_output(rsp.data, returns)

                return jsonify(rsp.to_dict())

            except ValidationError as e:
                return jsonify({
                    'result': 1,
                    'message': str(e),
                    'error': e.to_dict()
                }), e.error_code
            except Exception as e:
                return jsonify({
                    'result': -1,
                    'message': f'Internal error: {str(e)}'
                })

        setattr(wrapper, '_is_route', True)

        return wrapper

    return decorator


class ValidationError(Exception):
    """
    参数验证错误
    
    标准化的验证错误类，包含错误码、字段名、错误类型等信息
    """
    
    # 错误类型常量
    ERROR_MISSING_REQUIRED = 'MISSING_REQUIRED'  # 必填字段缺失
    ERROR_INVALID_TYPE = 'INVALID_TYPE'  # 类型错误
    ERROR_INVALID_FORMAT = 'INVALID_FORMAT'  # 格式错误
    ERROR_INVALID_VALUE = 'INVALID_VALUE'  # 值错误
    ERROR_VALIDATION_FAILED = 'VALIDATION_FAILED'  # 验证失败
    
    def __init__(self, message, field_name=None, error_type=None, error_code=400, value=None):
        """
        初始化验证错误
        
        Args:
            message: 错误消息
            field_name: 字段名称
            error_type: 错误类型（使用类常量）
            error_code: HTTP 错误码，默认 400
            value: 导致错误的原始值
        """
        super().__init__(message)
        self.message = message
        self.field_name = field_name
        self.error_type = error_type or self.ERROR_VALIDATION_FAILED
        self.error_code = error_code
        self.value = value
    
    def to_dict(self):
        """转换为字典格式，便于 JSON 序列化"""
        result = {
            'error': self.error_type,
            'message': self.message,
        }
        if self.field_name:
            result['field'] = self.field_name
        if self.value is not None:
            result['value'] = self.value
        return result
    
    def __str__(self):
        """格式化错误信息"""
        parts = [f"[{self.error_type}]"]
        if self.field_name:
            parts.append(f"字段 '{self.field_name}':")
        parts.append(self.message)
        if self.value is not None:
            parts.append(f"(值: {repr(self.value)})")
        return " ".join(parts)

# 验证入参
def validate_input(data, args_schema:dict):
    """验证输入参数"""
    if not args_schema:
        return {}

    result = {}
    for field_name, field in args_schema.items():
        value = data.get(field_name)

        # 处理必填字段
        if getattr(field, '_is_required', False):
            if value is None or value == '':
                raise ValidationError(
                    message=f'必填字段不能为空',
                    field_name=field_name,
                    error_type=ValidationError.ERROR_MISSING_REQUIRED,
                    value=value
                )

        # 使用字段的验证规则
        if value is not None and value != '':
            try:
                result[field_name] = field.validate(value)
            except ValidationError:
                # 如果是 ValidationError，直接抛出
                raise
            except Exception as e:
                # 其他异常包装为 ValidationError
                raise ValidationError(
                    message=f'字段值验证失败: {str(e)}',
                    field_name=field_name,
                    error_type=ValidationError.ERROR_INVALID_VALUE,
                    value=value
                )
        else:
            # 使用默认值
            result[field_name] = field.default

    return result
# 验证响应
def validate_output(data, returns_schema: dict):
    """验证输出数据"""
    if not returns_schema:
        return data

    # 将对象转为 dict 处理
    if data is None:
        payload = {}
    elif isinstance(data, dict):
        payload = data
    else:
        payload = getattr(data, '__dict__', {})

    result = {}
    for field_name, field in returns_schema.items():
        value = payload.get(field_name)

        if getattr(field, '_is_required', False):
            if value is None or value == '':
                raise ValidationError(
                    message=f'响应中必填字段不能为空',
                    field_name=field_name,
                    error_type=ValidationError.ERROR_MISSING_REQUIRED,
                    value=value
                )

        if value is not None and value != '':
            try:
                result[field_name] = field.validate(value)
            except ValidationError:
                # 如果是 ValidationError，直接抛出
                raise
            except Exception as e:
                # 其他异常包装为 ValidationError
                raise ValidationError(
                    message=f'响应字段值验证失败: {str(e)}',
                    field_name=field_name,
                    error_type=ValidationError.ERROR_INVALID_VALUE,
                    value=value
                )
        else:
            result[field_name] = field.default

    return result

class Field:
    """字段基类"""

    def __init__(self, desc='', default=None, is_required=False):
        self.desc = desc
        self.default = default
        self._is_required = is_required  # 标记是否为必填字段

    def validate(self, value):
        return value


class IntegerField(Field):
    def validate(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(
                message='必须是整数类型',
                error_type=ValidationError.ERROR_INVALID_TYPE,
                value=value
            )


class StringField(Field):
    def validate(self, value):
        if not isinstance(value, str):
            raise ValidationError(
                message='必须是字符串类型',
                error_type=ValidationError.ERROR_INVALID_TYPE,
                value=value
            )
        return value


class FieldWrapper:
    """
    字段包装器基类
    
    通过 __getattr__ 动态创建字段类，该类继承原始字段类并设置 _is_required 属性
    子类只需设置 _is_required 和 _field_types 即可
    """
    
    # 子类需要定义的字段类型映射
    _field_types = {
        'IntegerField': IntegerField,
        'StringField': StringField,
        'MessageField': Field,
    }
    
    def __init__(self, is_required=False):
        self._is_required = is_required
    
    def __getattr__(self, name):
        """动态创建字段类，该类会在实例化时设置 _is_required 属性"""
        if name in self._field_types:
            base_field_class = self._field_types[name]
            is_required = self._is_required
            
            # 动态创建继承自 base_field_class 的新类
            class WrappedField(base_field_class):
                def __init__(self, desc='', default=None):
                    super().__init__(desc=desc, default=default, is_required=is_required)
            
            # 设置类名以便调试
            WrappedField.__name__ = name
            WrappedField.__qualname__ = f"{self.__class__.__name__}.{name}"
            
            return WrappedField
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


class _RequiredWrapper(FieldWrapper):
    """必填字段包装器类"""
    def __init__(self):
        super().__init__(is_required=True)


class _OptionalWrapper(FieldWrapper):
    """可选字段包装器类"""
    def __init__(self):
        super().__init__(is_required=False)


class _RepeatedWrapper(FieldWrapper):
    """重复字段包装器类（通常用于列表）"""
    _field_types = {
        'MessageField': Field,
    }
    
    def __init__(self):
        super().__init__(is_required=False)


# 创建单例实例，这样 required.StringField 可以正常工作
required = _RequiredWrapper()
optional = _OptionalWrapper()
repeated = _RepeatedWrapper()


class RequestObject(object):
    """请求对象，用于存储验证后的参数"""

    def __init__(self):
        self._data = {}

    def update(self, data):
        self._data.update(data)

    def __getattr__(self, name):
        return self._data.get(name)


class ResponseObject(object):
    """响应对象，用于格式化返回值"""

    def __init__(self):
        self.result = 0
        self.message = 'ok'
        self.data = None

    def new(self):
        return type('ResponseData', (), {})()

    def to_dict(self):
        if self.data is None:
            data_obj = None
        elif isinstance(self.data, dict):
            data_obj = self.data
        else:
            data_obj = getattr(self.data, '__dict__', None)

        return {
            'result': self.result,
            'message': self.message,
            'data': data_obj
        }

