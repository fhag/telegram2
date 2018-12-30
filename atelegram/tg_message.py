# -*- coding: utf-8 -*-
'''
Class for storing telegram messages for easy access
'''
from keyword import iskeyword


class Msg(object):
    '''class for easy access to telegram messages'''
    def __init__(self, msg, bot_name=None):
        if bot_name:
            self.bot_name = bot_name
#        logger.info(msg)
        _msg = {k + '_': v for k,v in msg.items() if iskeyword(k)}
        _msg.update({k: v for k, v in msg.items() if not iskeyword(k)})
        for key in _msg.keys():
            if isinstance(_msg[key], dict):
                self.__dict__.update({key: Msg(_msg[key])})
            else:
                self.__dict__.update({key: _msg[key]})

    def __bool__(self):
        return True if len(self) > 1 else False

    def __len__(self):
        return len(self.__dict__)

    def __repr__(self):
        return str({k: v for k, v in self.__dict__.items()})