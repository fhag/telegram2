# -*- coding: utf-8 -*-
'''
Class Atelegram

functions to receive and send Telegram messages
through async.Queue

'''

import json
import asyncio
import async_timeout
import sys
import yaml
from arequests.arequests import (Arequests, SomeClientError,
                                 SomeServerError, AuthorizationError)
from .atelegram_log import logger
from .tg_bot import Bot
from .tg_message import Msg

__version__ = '0.0.6'
print(f'Imported Telegram from telegram.py v{__version__}')

# read yaml file with configuration data
with open("atelegram/atelegram.yml", 'r') as stream:
    tg_config = yaml.load(stream)

class Atelegram(Arequests):
    '''functions for receiving and sending telegrams'''
    def __init__(self, config, max_connections=None):
        if not config:
            raise ValueError('missing config data')
        self.cfg = config
        self.bots = dict()
        self.in_msgs = None
        self.out_msgs = None
        self.task_out_msgs = None
        super().__init__(max_connections=max_connections)
        logger.debug('Telegram initialised')

    async def __aenter__(self):
        logger.info('aenter')
        await super().__aenter__()
        await self._initialise_bots()
        await self._initialise_msgs_loops()
        for i, task in enumerate(asyncio.all_tasks()):
            logger.info(f'{i:3.0f}. {task}')
        logger.info('aenter finished')
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        logger.info('- start end -' * 19)
        await self._shutdown_loop_in_msgs()
        await asyncio.sleep(0)
        await super().__aexit__(exc_type, exc_value, exc_traceback)
        logger.info('- end -' * 20)
        return False

    def __enter__(self):
        raise TypeError("Use async with instead")

    def __exit__(self, exc_type, exc_val, exc_tb):
        # __exit__ should exist in pair with __enter__ but never executed
        pass  # pragma: no cover

    async def _initialise_bots(self):
        '''getMe data to update bots and check validity'''
        for bot_name in self.cfg['bots'].keys():
            self.bots[bot_name] = Bot(self.cfg['bots'][bot_name],
                                      self.cfg['telegram_url'])
            print(f'{bot_name} initialised')
            try:
                response = await self.agetMe(bot_name=bot_name)
                assert response, 'not ok'
                assert response.is_bot, 'is not a bot'
                old_msgs = await self.agetUpdates(offset=0, bot_name=bot_name)
                del old_msgs
            except AssertionError as err:
                logger.error(f'{bot_name}: {err}', exc_info=False)
                del self.bots[bot_name]
            else:
                logger.info(response)
                self.bots[bot_name].__dict__.update(response.__dict__)
        del self.cfg['bots']

    async def _initialise_msgs_loops(self):
        '''loop polling all active telegram bots and put msgs on queue'''
        for bot_name in self.bots:
            self.bots[bot_name].task = asyncio.create_task(
                self._loop_in_msgs(bot_name=bot_name))
        self.task_out_msgs = asyncio.create_task(self._loop_out_msgs())

    async def _shutdown_loop_in_msgs(self):
        '''shutdonw _loop_in_msgs for all bot_name'''
        tasks = {self.bots[bot_name].task for bot_name in self.bots}
        tasks.add(self.task_out_msgs)
        for i, task in enumerate(tasks):
            task.cancel()
            async with async_timeout.timeout(0.5):
                await task

    async def _loop_in_msgs(self, bot_name=None):
        '''loop to collect tg messages from single bot'''
        self.in_msgs = asyncio.Queue()
        while True:
            try:
                msgs = await self.aget_new_Updates(bot_name=bot_name)
            except asyncio.CancelledError:
                break
            except Exception as err:
                ftext = f'{bot_name}: {err}'
                logger.error(ftext, exc_info=True)
                msg = Msg(dict(message=dict(text=ftext), bot_name=bot_name))
                await self.in_msgs.put(msg)
            else:
                for msg in msgs:
                    await self.in_msgs.put(msg)
                    ftext = f'in -> {self.in_msgs.qsize()}. {msg.bot_name!r}'
#                    logger.info(f'{ftext} : {msg.message!r}')
            await asyncio.sleep(self.cfg['wait_between_msgs_looping'])

    async def _loop_out_msgs(self):
        '''send whatever msg in queue to destination bot'''
        self.out_msgs = asyncio.Queue()
        while True:
            try:
                msg = await self.out_msgs.get()
                logger.debug(f'out_msg ->{msg}')
                ftext = 'ERROR: missing out_text in msg'
                text = msg.out_text if hasattr(msg, 'out_text') else ftext
                bot_name = msg.bot_name
                chat_id = msg.message.from_.id
#                reply_to_message_id = msg.message.message_id
                msg_sent = await self.asend_message(text, bot_name, chat_id)
                logger.debug(msg_sent)
                logger.debug(msg)
                assert msg_sent, msg
            except AssertionError:
                logger.error(f'msg:{msg!r} was not sent', exc_info=False)
                await self.out_msgs.put(msg)
                await asyncio.sleep(self.cfg['wait_out_msgs_not_sent'])
            except AttributeError as err:
                logger.error(f'msg:{msg} incomplete,\n    was not sent: {err}',
                             exc_info=False)
            except asyncio.CancelledError:
                logger.error('_loop_out_msgs cancelled')
                break
            except Exception as err:
                logger.error(f'msg:{msg} not sent: {err}', exc_info=True)
            await asyncio.sleep(self.cfg['wait_between_msgs_looping'])

    async def _aget_method(self, method='method', bot=None, params=None,
                           maxtrials=None, readtimeout=None) -> dict():
        '''
        generalized request to telegram
        returns answer from telegram as json object
        loops if no answer provided
        '''
        maxtrials = (self.cfg['get_method_maxtrials'] if
                     maxtrials is None else maxtrials)
        readtimeout = (self.cfg['get_method_readtimeout'] if
                       readtimeout is None else readtimeout)
        url = bot.url + method
        while maxtrials > 0:
            try:
                response = await self.get_json(url,
                                               params=params,
                                               timeout=readtimeout)
            except (TimeoutError, SomeClientError, SomeServerError) as err:
                maxtrials -= 1
                logger.debug(
                        f'{err}: {bot.bot_name!r}: {maxtrials} trials left')
                await asyncio.sleep(self.cfg['get_method_sleeptime'])
            except asyncio.CancelledError:
                raise asyncio.CancelledError ('abort routine')
            except (AuthorizationError, Exception) as err:
                exc_type, exc_value, traceb = sys.exc_info()
                ftext = f'{err}|{exc_type}|{exc_value}|{traceb}'
                logger.error(ftext, exc_info=True)
                maxtrials = 0
            else:
                return response
        logger.error('ERROR: failed to get data')
        return dict(ok=False, result=list())

    async def agetMe(self, bot_name=None):
        '''returns basic information about chat '''
        response = await self._aget_method(method='getMe',
                                           bot=self.bots[bot_name])
        if response['ok']:
            return Msg(response['result'], bot_name=bot_name)
        logger.error(response)
        return Msg(dict(), bot_name=bot_name)

    async def aget_new_Updates(self, bot_name=None,
                               maxtrials=None, readtimeout=None) -> list:
        '''returns list of new messages'''
        return await self.agetUpdates(bot_name=bot_name, offset='onlyNewMsgs',
                                      maxtrials=maxtrials,
                                      readtimeout=readtimeout)

    async def agetUpdates(self, offset='onlyNewMsgs', bot_name=None,
                          maxtrials=None, readtimeout=None) -> list:
        '''offset:
                default -> get all new messages
                0       -> get all messages
                -n      -> get last n messages'''
        async def emsg(msg):
            '''replace attribute edited_message with message'''
            if hasattr(msg, 'message'):
                return msg
            msg.message = msg.edited_message
            del msg.edited_message
            return msg

        if offset == 'onlyNewMsgs':
            offset = self.bots[bot_name].last_update_id + 1
        params = {'offset': offset,
                  'allowed_updates': ['message', 'edited_message']}
        responses = await self._aget_method(method='getUpdates',
                                            bot=self.bots[bot_name],
                                            params=params,
                                            maxtrials=maxtrials,
                                            readtimeout=readtimeout)
        if responses['ok'] and responses['result']:
            for result in responses['result']:
                logger.info(result)
            msgs = [await emsg(Msg(result, bot_name=bot_name)) for result
                    in responses['result']]
            self.bots[bot_name].last_update_id = msgs[-1].update_id
            return msgs
        return []

    async def asend_message(self, text, bot_name, chat_id,
                            params=None) -> bool:
        ''' send a message to the specified chat
        parameters:
            text    = 'text msg' (string)
            chat_id = valid chat id number (intger)
        output:
            full reply -> if successful
            False -> if not successful
        '''
        params = dict() if params is None else params
        params.update({'text': text, 'chat_id': chat_id})
        params.update({'parse_mode': 'HTML'})
        params.setdefault('reply_markup', json.dumps({'remove_keyboard':True}))
        ftext = f'\n{" "*17}bot_name:{bot_name!r}:  chat_id:{chat_id!r}  '
        logger.info(f'{ftext}  text:{text!r}\n{" "*17}params: {params}\n')
        try:
            reply = await self._aget_method(method='sendMessage',
                                            bot=self.bots[bot_name],
                                            params=params)
        except KeyError as err:
            logger.error(err, exc_info=True)
            return False
        except asyncio.CancelledError as err:
            logger.error(err, exc_info=False)
            return False
        except Exception as err:
            logger.error(err, exc_info=True)
            return False
        else:
            logger.info(reply)
            return reply
