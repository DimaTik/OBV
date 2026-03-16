import asyncio
import configparser
import functools
import inspect
import pathlib
import time
from asyncio import CancelledError
from contextlib import asynccontextmanager, contextmanager
from json import JSONDecodeError
from typing import Callable

from aiodns.error import DNSError
from aiohttp import ClientError
from ccxt.base.errors import RequestTimeout, InvalidNonce, InvalidOrder, ExchangeError, ExchangeNotAvailable, \
	NetworkError


class ConfigHandler:
	def __init__(self):
		self.config = configparser.ConfigParser()
		self.update_config()

	def update_config(self):
		while True:
			path = pathlib.PurePath(__file__)
			config_arr = self.config.read(f'{path.parent}/config.ini')
			if not config_arr:
				print('Файл config не найден')
				time.sleep(5)
			else:
				break

	def get_api(self) -> tuple[str, str]:
		return self.config[f'BYBIT']['api_public'].strip(), \
			self.config[f'BYBIT']['api_secret'].strip()

	def get_indicator_settings(self) -> dict:
		return {"tf": self.config['INDICATOR']['timeframe'],
		        "obv_length": self.config['INDICATOR']['obv_length'],
		        "ma_type": self.config['INDICATOR']['ma_type'],
		        "ma_length": self.config['INDICATOR']['ma_length'],
		        "macd_slow_length": self.config['INDICATOR']['macd_slow_length'],
		        "len5": self.config['INDICATOR']['len5'],
		        "period": int(self.config['INDICATOR']['period'])}

	def get_order_settings(self):
		return {"volume": int(self.config['ORDER']['volume']),
				"leverage": int(self.config['ORDER']['leverage'])}


class ApiCallResult:
	def __init__(self):
		self.error = None

@asynccontextmanager
async def asafe(fn):
	api_result = ApiCallResult()
	try:
		yield api_result
	except (
	ClientError, JSONDecodeError, RequestTimeout, DNSError, InvalidNonce, NetworkError, CancelledError) as e:
		print(e.__class__.__name__, e, fn)
		api_result.error = e.args
		await asyncio.sleep(3)
	except (InvalidOrder, ExchangeError, ExchangeNotAvailable) as e:
		print(e.__class__.__name__, e, fn)
		api_result.error = e.args
		await asyncio.sleep(3)
	except (ValueError, TimeoutError) as e:
		print(e.__class__.__name__, e, fn)
		api_result.error = e.args
		await asyncio.sleep(3)

@contextmanager
def safe(fn):
	api_result = ApiCallResult()
	try:
		yield api_result
	except (
	ClientError, JSONDecodeError, RequestTimeout, DNSError, InvalidNonce, NetworkError, CancelledError) as e:
		print(e.__class__.__name__, e, fn)
		api_result.error = e.args
		time.sleep(3)
	except (InvalidOrder, ExchangeError, ExchangeNotAvailable) as e:
		print(e.__class__.__name__, e, fn)
		api_result.error = e.args
		time.sleep(3)
	except (ValueError, TimeoutError) as e:
		print(e.__class__.__name__, e, fn)
		api_result.error = e.args
		time.sleep(3)

def retry(fn: Callable) -> Callable:
	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		for _ in range(3):
			with safe(fn) as s:
				res = fn(*args, **kwargs)
				if s.error is None:
					return res
		raise Exception('Насяльника я не справился... Хер знает че тут произошло')

	@functools.wraps(fn)
	async def awrapper(*args, **kwargs):
		for _ in range(3):
			async with asafe(fn) as s:
				res = await fn(*args, **kwargs)
				if s.error is None:
					return res
		raise Exception('Насяльника, извини, я не справился... Хер знает че ты от меня хочешь')

	if inspect.iscoroutinefunction(fn):
		return awrapper
	else:
		return wrapper
