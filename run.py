import os
from urllib.parse import unquote

from flask import url_for

import config
from app import app as my_app
from app.loggers import logger

if config.LIST_ROUTES:
    with my_app.test_request_context():
        output = []
        for rule in my_app.url_map.iter_rules():
            if rule.endpoint.startswith('apilist.'):
                continue

            options = {}
            for arg in rule.arguments:
                options[arg] = '[%s]' % arg

            methods = ','.join(rule.methods)
            url = url_for(rule.endpoint, **options)
            output.append((rule.endpoint, unquote(url), methods))

        max_len = [
            (max([len(o[i]) for o in output]) / 4 + 2) * 4 for i in range(3)]
        for (endpoint, url, methods) in sorted(output):
            logger.debug('%-{0}s %s'.format(*max_len) %
                         (endpoint, url))

if __name__ == '__main__':
    from typing import Any, Dict

    # SVR_CONFIG 包含混合类型（str 和 bool），需要明确类型注解
    svr_cfg: Dict[str, Any] = dict(**config.SVR_CONFIG)
    if os.environ.get('SUBLIMETEXT'):
        logger.debug('disable flask debug')
        svr_cfg['debug'] = False  # Flask.run() 的 debug 参数确实是 bool 类型
    my_app.run(**svr_cfg)
