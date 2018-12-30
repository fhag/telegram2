'''
class for async requests with all exceptions handled
'''
import asyncio
import typing
import concurrent
from json import JSONDecodeError
import aiohttp
from aiohttp import hdrs
from .exceptions import (SomeClientError, SomeServerError, AuthorizationError)
from .arequests_log import logger


__version__ = '0.0.11'

logger.debug('{} arequests v{}'.format(__name__, __version__))
logger.debug(f'mytrainer.py{__version__} started')

logger.debug(f'arequests.py{__version__} started')

class Arequests():
    ''' finding address from coordinates with cache or google'''
    def __init__(self, max_connections=None):
        self.restart = None
        self.session_counter = None
        self.closed = None
        self.session = None
        self.max_connections = max_connections
        self.start_task = None
        logger.debug('Arequests initialised')

    async def __aenter__(self):
        self.start_task = asyncio.create_task(self._start())
        logger.debug('context entered with start()')
        await asyncio.sleep(0)
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        await self._shutdown()
        if exc_value:
            logger.error(exc_value, exc_info=True)
        logger.debug('context exited')
        await asyncio.sleep(0)
        return True

    def __enter__(self):
        raise TypeError("Use async with instead")

    def __exit__(self, exc_type, exc_val, exc_tb):
        # __exit__ should exist in pair with __enter__ but never executed
        pass  # pragma: no cover

    async def _reset(self):
        ''' reset session and restart new session'''
        self.closed.set()
        logger.debug('session _reset')
        await asyncio.sleep(0)

    async def _shutdown(self):
        '''close session and do not restart new session'''
        self.restart = False
        self.closed.set()
        await asyncio.sleep(0)
        logger.debug('_shutdown executed')

    async def _start(self):
        '''start session and keep alive for requests'''
        self.session_counter = 1
        self.restart = True
        self.closed = asyncio.Event() # prepare Flag
        connector = aiohttp.TCPConnector(limit=self.max_connections)
        while True:
            async with aiohttp.ClientSession(raise_for_status=True,
                                             connector=connector) as session:
                self.session = session
                logger.debug(f'{__name__!r} session nr ' +
                             f'{self.session_counter} initialized')
                await self.closed.wait()
            if self.restart:
                self.closed.clear()
                self.session_counter += 1
                logger.info('session_counter + 1 to %s', self.session_counter)
            else:
                break
        logger.info('self.session closed and start() terminated')

    async def get_json(self, url, params=None,
                       **kwargs) -> typing.Union[str, dict]:
        '''Perform HTTP GET request response and returns .'''
        kwargs.setdefault('allow_redirects', True)
        return await self._request(hdrs.METH_GET, url, json=True,
                                   data=params, **kwargs)

    async def get_text(self, url, params=None,
                       **kwargs) -> typing.Union[str, dict]:
        '''Perform HTTP GET request response and returns .'''
        kwargs.setdefault('allow_redirects', True)
        return await self._request(hdrs.METH_GET, url, data=params,
                                   json=False, **kwargs)

    async def post_json(self, url,
                        data=None, **kwargs) -> typing.Union[str, dict]:
        '''Perform HTTP GET request and return text'''
        return await self._request(hdrs.METH_POST, url, json=True,
                                   data=data, **kwargs)

    async def post_text(self, url,
                        data=None, **kwargs) -> typing.Union[str, dict]:
        '''Perform HTTP GET request and return text'''
        return await self._request(hdrs.METH_POST, url, json=False,
                                   data=data, **kwargs)

    async def _check_session(self):
        '''make sure session is alife'''
        try:
            assert not self.session.closed
        except AttributeError:
            logger.debug('-->launch self._start and open self.session')
            self.start_task = asyncio.create_task(self._start())
            await asyncio.sleep(0) # leave time to setup start loop
        except AssertionError:
            logger.debug('--> reset for a new self.session')
            await self._reset()
            await asyncio.sleep(0)

    async def _request(self, method, url, json=False,
                       data=None, **kwargs) -> typing.Union[str, dict]:
        '''Perform HTTP request'''
        await asyncio.sleep(0)
        try:
            await self._check_session()
            async with self.session.request(method, url, data=data,
                                            **kwargs, raise_for_status=True
                                            ) as response:
                text = await response.text()
                if json:
                    try:
                        text = await response.json(content_type=None)
                    except (JSONDecodeError, TypeError) as err:
                        logger.error(err)
                        text = str(err)
                    except Exception as err:
                        ftext = f'Unknown exception with JSON: {err}'
                        logger.error(ftext, exc_info=True)
                        text = ftext
                if text['result']:
                    logger.debug(f'normal return with {text!r}')
                return text
        except aiohttp.ClientError as err:
            logger.error(f' {url}: {err}', exc_info=False)
            err_code = str(err)[:3]
            if err_code == '401': # 401
                logger.debug(' raise AuthorizationError')
                raise AuthorizationError(err)
            elif err_code[0] == '4': # 4xx
                logger.debug(f' raise SomeClientError:{err}')
                raise SomeClientError(err)
            logger.debug(' raise SomeServerError')
            raise SomeServerError(err)
        except asyncio.TimeoutError as err:
            logger.debug(f' {url}:{err}', exc_info=False)
            raise TimeoutError(f' {url}:{err}')
        except (asyncio.CancelledError,
                concurrent.futures.CancelledError,
                RuntimeError) as err:
            etext = f'Terminating with: {err.__repr__()}'
            logger.error(etext, exc_info=False)
            raise asyncio.CancelledError ('abort operation')
        except Exception as err:
            etext = f'Any other error: {err.__repr__()}'
            logger.error(etext, exc_info=True)
            raise Exception(etext)
