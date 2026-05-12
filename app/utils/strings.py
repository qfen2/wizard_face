def split_string(string: str, to_int: bool = False, key: str = ',') -> list:
    """分割字符串为列表"""
    if string == '' or string is None:
        return []
    string = string.replace('{}{}'.format(key, key), key).strip(key)
    if to_int:
        return [int(i) for i in string.strip(key).split(key) if i]
    return [i for i in string.strip(key).split(key) if i]