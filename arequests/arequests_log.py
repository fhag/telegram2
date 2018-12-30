# -*- coding: utf-8 -*-
"""
Logger for Arequests

Created on Tue Nov 13 08:34:14 2018
@author: gfi
"""
import logging

__version__ = '0.0.1'


logger = logging.Logger('arequests')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('arequests.log', mode='w')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s|%(filename)24s|%(levelname)7s|%(funcName)26s|' +
    '%(lineno)3d|%(process)d|%(thread)d|%(message)s',
    "%d%b%y %H:%M.%S")
handler.setFormatter(formatter)
logger.addHandler(handler)