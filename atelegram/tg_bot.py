# -*- coding: utf-8 -*-
'''
Class for bot access data
access usually through bot_name
'''
__version__ = '0.0.1'

print(f'Loading tb_bot.py v{__version__}')

class Bot(object):
    '''class for bot access data'''
    def __init__(self, data, url_form):
        self.__dict__.update(data)
        self.id = data.get('id', 0)
        self.username = data.get('username', 'nn')
        self._url_form = url_form
        self.last_update_id = 0
        assert hasattr(self, 'token'), 'Please provide token'
        assert self.url != self._url_form, 'url form missing {} for token'

    @property
    def url(self):
        '''return url including token'''
        return self._url_form.format(self.token)

    def __len__(self):
        return len(self.__dict__)

    def __repr__(self):
        return str({k: v for k, v in self.__dict__.items()})