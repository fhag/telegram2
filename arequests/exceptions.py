# -*- coding: utf-8 -*-
"""
Exceptions for Arequests

Created on Tue Nov 13 08:34:14 2018
@author: gfi
"""

class ArequestsError(Exception):
    """Basic exception for errors raised by Arequests"""
    pass

class AuthorizationError(ArequestsError):
    '''401 error new authentification required'''
    pass

class SomeClientError(ArequestsError):
    '''4xx client error'''
    pass

class SomeServerError(ArequestsError):
    '''5xx server error'''
    pass
