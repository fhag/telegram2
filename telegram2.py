'''
'''
__version__ = '0.0.1'

# -*- coding: utf-8 -*-
"""
Created on Tue Nov 27 22:33:02 2018
Running math test for single user
@author: annet
"""
import asyncio

import logging
import random
from atelegram.atelegram import Atelegram
from atelegram.tg_message import Msg


config = {'telegram_url': 'https://api.telegram.org/bot{}/',
          'bots': {'mytestbot':
                   {'first_name': 'mytestbot',
                    'token': 'mytoken'}},
               'get_method_maxtrials': 4, 'get_method_sleeptime': 1,
               'get_method_readtimeout': 3.1, 'wait_between_msgs_looping': 0.1,
               'wait_out_msgs_not_sent': 10}

logger = logging.Logger('telegram2')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('telegram2.log', mode='w')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s|%(filename)24s|%(levelname)7s|%(funcName)26s|' +
    '%(lineno)3d|%(process)d|%(thread)d|%(message)s',
    "%d%b%y %H:%M.%S")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info(f'telegram1 version {__version__} started')

__version__ = '0.0.4'
print('{} mytrainer v{}'.format(__name__, __version__))
logger.debug('{} mytrainer v{}'.format(__name__, __version__))
logger.debug(f'mytrainer.py{__version__} started')

class Headtrainer():
    '''runs mytrainer'''
    def __init__(self, config):
        logger.info(config)
        self.cfg = config
        self.users = dict()
        self.check_idle_task = None


    async def handle_msg(self, msg, out_msgs):
        '''handle message'''
        msg.out_text = f'out:{msg.message.text}'
        await out_msgs.put(msg)
        return

    async def loop_rnd_msg(self, tg):
        out_msgd = {'bot_name':'mytestbot', 'message':{'from':{'id':320858040}}}
        while True:
            await asyncio.sleep(4)
            msg_text =f'msg {random.randint(0, 12)}'
            out_msgd.update({'out_text':msg_text})
            await tg.out_msgs.put(Msg(out_msgd))


    async def main(self):
        '''Main loop to collect telegram messages and handle them'''
        try:
            async with Atelegram(self.cfg) as tg:
                logger.info(tg.bots.keys())
                self.loop_task = asyncio.create_task(self.loop_rnd_msg(tg))
                await asyncio.sleep(0)
                logger.info('start while loop')
                while True:
                    msg = await tg.in_msgs.get()
                    logger.info(msg)
                    if hasattr(msg.message, 'text'):
                        if msg.message.text.lower() == 'stopp':
                            msg.out_text = 'stopping mytrainer'
                            await tg.out_msgs.put(msg)
                            self.loop_task.cancel()
                            try:
                                self.check_idle_task.cancel()
                                for (key, user) in self.users.items():
                                    user.run_task.cancel()
                                    await asyncio.sleep(0)
                                await asyncio.sleep(0)
                                logger.info('break from stopp')
                            except Exception as err:
                                logger.debug(err, exc_info=True)
                            break
                        await self.handle_msg(msg, tg.out_msgs)
                    else:
                        msg.out_text = f'No valid attribute message {msg.message}'
                        tg.out_msgs.put(msg)
                logger.info('finished while loop')
        except asyncio.CancelledError:
            logger.error('main cancelled', exc_info=False)
        except Exception as err:
            logger.error(err, exc_info=True)
        try:
            logger.info('closed Atelegram')
            logger.info('main terminated')
        except Exception as err:
            logger.error(err, exc_info=True)
        return


if __name__ == '__main__':
    print('Starte Programm')
    trainer = Headtrainer(config)
    try:
        asyncio.run(trainer.main(), debug=False)
    except Exception as err:
        logger.error(err, exc_info=True)
    logger.info('fertig')
    print('fertig')
