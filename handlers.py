import configparser
import functools
import pathlib
import time
from asyncio import CancelledError
from contextlib import contextmanager
from json import JSONDecodeError
from typing import Callable

from aiodns.error import DNSError
from aiohttp import ClientError
from ccxt.base.errors import RequestTimeout, InvalidNonce, InvalidOrder, ExchangeError, ExchangeNotAvailable, \
	NetworkError

from log import logger


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

	def get_exchange_settings(self) -> dict:
		return {'api_public': self.config['BYBIT']['api_public'].strip(),
		        'api_secret': self.config['BYBIT']['api_secret'].strip(),
		        'mode': False if self.config['BYBIT']['mode'] == 'DEMO' else True}

	def get_user_tickers(self):
		return tuple([i.strip() for i in self.config['BYBIT']['tickers'].split(',')])

	def get_indicator_settings(self) -> dict:
		return {"tf": self.config['INDICATOR']['timeframe'],
		        "obv_length": int(self.config['INDICATOR']['obv_length']),
		        "macd_fast": int(self.config['INDICATOR']['macd_fast']),
		        "macd_slow": int(self.config['INDICATOR']['macd_slow']),
		        "macd_signal": int(self.config['INDICATOR']['macd_signal']),
		        "stoch_k": int(self.config['INDICATOR']['stoch_k']),
		        "stoch_d": int(self.config['INDICATOR']['stoch_d']),
		        "stoch_smooth": int(self.config['INDICATOR']['stoch_smooth']),
		        "sma_lenght": int(self.config['INDICATOR']['sma_lenght'])}

	def get_indicator_weights_settings(self) -> dict:
		return {"macd": float(self.config['INDICATOR.WEIGHTS']['macd']),
		        "stochastic": float(self.config['INDICATOR.WEIGHTS']['stochastic']),
		        "obv": float(self.config['INDICATOR.WEIGHTS']['obv']),
		        "ma": float(self.config['INDICATOR.WEIGHTS']['ma']),
		        "vol": float(self.config['INDICATOR.WEIGHTS']['vol'])}

	def get_order_settings(self):
		return {"volume_const": float(self.config['ORDER']['volume_const']),
		        "volume_percent": float(self.config['ORDER']['volume_percent']) / 100,
		        "leverage": int(self.config['ORDER']['leverage']),
		        "grid_step_percent": float(self.config['ORDER']['grid_step_percent']) / 100, }

	def get_risk_management(self):
		return {"TP": float(self.config['RISK']['TP']) / 100,
		        "SL": float(self.config['RISK']['SL']) / 100,
		        "simple_TP_percent": float(self.config['RISK']['simple_TP_percent']) / 100,
		        "trailing_trigger_percent": float(self.config['RISK']['trailing_trigger_percent']) / 100,
		        "trailing_stop_percent": float(self.config['RISK']['trailing_stop_percent']) / 100}

	def get_proxy(self):
		return self.config['PROXY']['http']

	def get_control_word(self):
		return self.config['OTHER']['control_word']


class ApiCallResult:
	def __init__(self):
		self.error = None


@contextmanager
def safe(fn):
	api_result = ApiCallResult()
	try:
		yield api_result
	except (
			ClientError, JSONDecodeError, RequestTimeout, DNSError, InvalidNonce, NetworkError, CancelledError) as e:
		logger.info(f'{e.__class__.__name__} {e} {fn}')
		api_result.error = e.args
		time.sleep(3)
	except (InvalidOrder, ExchangeError, ExchangeNotAvailable) as e:
		logger.info(f'{e.__class__.__name__} {e} {fn}')
		api_result.error = e.args
		time.sleep(3)
	except (ValueError, TimeoutError) as e:
		logger.info(f'{e.__class__.__name__} {e} {fn}')
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
		raise Exception('Извини я не справился... Не знаю что тут произошло')

	return wrapper
