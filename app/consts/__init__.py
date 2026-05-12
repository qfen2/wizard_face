#!-*- coding=utf-8 -*-

import inspect
import collections

__all__ = [
    'Item',
    'ConstGroup',
]

class Item(object):
    def __init__(self, value, title):
        self._value = value
        self._title = title
        self._key   = ''

    @property
    def value(self):
        return self._value

    @property
    def title(self):
        return self._title

    @property
    def key(self):
        return self._key

    def __get__(self, obj, cls):
        return self._value


class ConstGroup(object):
    __title_map__ = collections.OrderedDict()

    @classmethod
    def _get_title_map(cls):
        if not '__title_map__' in cls.__dict__:
            for field, _ in inspect.getmembers(cls):
                field_obj = cls.__dict__.get(field, None)
                if not isinstance(field_obj, Item):
                    continue
                if field_obj.value in cls.__title_map__:
                    raise ValueError('Duplicated const value %s in group %s' \
                        % (str(field_obj.value), cls.__name__))
                cls.__title_map__[field_obj.value] = field_obj.title
            for base_cls in cls.__bases__:
                if not issubclass(base_cls, ConstGroup):
                    continue
                cls.__title_map__.update(base_cls._get_title_map())
        return cls.__title_map__

    @classmethod
    def get_title(cls, value, default = ''):
        return cls._get_title_map().get(value, default)

    @classmethod
    def get_title_dict(cls):
        return cls._get_title_map()

    @classmethod
    def get_choices(cls):
        choices = list(cls._get_title_map().items())
        choices.sort(key = lambda item: item[0])
        return choices

    @classmethod
    def has_value(cls, value):
        return value in cls._get_title_map()

    @classmethod
    def get_value(cls, title, default=''):
        try:
            if not isinstance(title, str):
                title = title.decode('u8')
        except:
            pass
        for k, v in cls._get_title_map().items():
            if v == title:
                return k
        return default