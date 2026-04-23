import time
from datetime import datetime, timedelta

import ccxt
from ccxt.base.errors import BadRequest
from pybit.unified_trading import HTTP

import handlers


class Exchange:
	def __init__(self, api_key, api_secret, mode, proxy, tp, sl, simple_tp_percent, trailing_trigger_percent,
	             trailing_stop_percent, grid_step):
		self.api_key = api_key
		self.api_secret = api_secret
		self.mode = mode
		self.proxy = proxy
		self.tp = tp
		self.sl = sl
		self.simple_tp_percent = simple_tp_percent
		self.trailing_trigger_percent = trailing_trigger_percent
		self.trailing_stop_percent = trailing_stop_percent
		self.grid_step = grid_step
		self.api_params = {
			"apiKey": self.api_key,
			"secret": self.api_secret,
			"enableRateLimit": True,
		}
		if proxy:
			self.api_params['aiohttp_proxy'] = proxy
			self.api_params['proxies'] = {
				'http': self.proxy,
				'https': self.proxy
			}
		self.cex = ccxt.bybit(self.api_params)
		if self.mode:
			self.cex.enable_demo_trading(True)

		self.session_bybit = HTTP(
			testnet=False,
			demo=self.mode,
			api_key=self.api_key,
			api_secret=self.api_secret
		)

	@handlers.retry
	def get_balance(self, token):
		return self.cex.fetch_balance()[token]['free']

	@handlers.retry
	def get_price(self, ticker):
		return self.cex.fetch_ticker(ticker)['last']

	@handlers.retry
	def get_btc_tickers(self):
		tickers = self.cex.fetch_markets()
		tickers = [i['symbol'] for i in tickers if (i['symbol'][:8] == 'BTC/USDT' and i['symbol'][-1] not in ('P', 'C'))
		           or i['symbol'][:8] == 'BTC/USDC']
		return tickers

	@handlers.retry
	def get_ohlcv(self, timeframe, tickers) -> dict:
		candles = {i: self.cex.fetch_ohlcv(i, timeframe, limit=300) for i in tickers}
		return candles

	@handlers.retry
	def preparation_derivative(self, ticker, leverage):
		try:
			self.cex.set_margin_mode('isolated', ticker, params={'leverage': leverage})
			self.cex.set_leverage(symbol=ticker, leverage=leverage)
		except BadRequest:
			pass

	@handlers.retry
	def get_position(self, symbol):
		position = self.cex.fetch_position(symbol)
		if not position['contracts']:
			return None
		return ['buy' if position['side'] == 'long' else 'sell', position['contracts'] * position['contractSize']]

	@handlers.retry
	def get_last_order(self, ticker):
		timestamp = (int(time.time()) - 14700) * 1000  # 4 часа 5 минут (из-за максимального TF 4h)
		orders = self.cex.fetch_closed_orders(ticker, since=timestamp)
		if not orders or not orders[-1]['amount']:
			return None
		return [orders[-1]['side'], orders[-1]['filled']]

	def _to_pybit_market(self, symbol: str):
		if ':' in symbol:
			base_quote, settle = symbol.split(':', 1)
			base, quote = base_quote.split('/')
			return f'{base}{quote}', 'linear' if settle in ('USDT', 'USDC') else 'inverse'
		base, quote = symbol.split('/')
		return f'{base}{quote}', 'spot'

	def _offsets(self, order_side: str):
		return range(-2, 1) if order_side == 'buy' else range(0, 3)

	def _calculation_price(self, base_price, i, side):
		return base_price * (1 + i * self.grid_step) if side == 'buy' \
			else base_price * (1 - i * self.grid_step)

	@handlers.retry
	def create_orders(self, ticker, side: str, amount: float):  # amount в BTC
		pybit_symbol, category = self._to_pybit_market(ticker)
		if category == 'spot':
			self.cex.cancel_all_orders(ticker, params={'trigger': True})
		base_price = self.get_price(ticker)
		batch_orders = []
		for i in self._offsets(side):
			limit_price = float(self.cex.price_to_precision(ticker, self._calculation_price(base_price, i, side)))
			order_qty = float(self.cex.amount_to_precision(ticker, amount))
			batch_orders.append(
				{
					'symbol': pybit_symbol,
					'isLeverage': 0,
					'side': side.capitalize(),
					'orderType': 'Limit',
					'qty': str(order_qty),
					'price': str(limit_price),
					# 'timeInForce': 'GTC',
				}
			)
		response = self.session_bybit.place_batch_order(category=category, request=batch_orders)
		result = response.get('result', {})
		placed = result.get('list', [])
		orders = [order['orderId'] for order in placed if order.get('orderId')]
		return orders

	@handlers.retry
	def create_tp_sl(self, ticker, orders_ids, leverage):
		bybit_symbol = ticker.replace('/', '').split(':')[0]
		if leverage:
			position = self.cex.fetch_position(ticker)
			if position['side'] == 'short':
				self.session_bybit.set_trading_stop(
					category="linear",
					symbol=bybit_symbol,
					positionIdx=0,
					tpLimitPrice=str(self.cex.price_to_precision(ticker, position['entryPrice'] * (1 - self.tp))),
					takeProfit=str(self.cex.price_to_precision(ticker, position['entryPrice'] * (1 - self.tp))),
					tpSize=str(position['contractSize'] * position['contracts'] * self.simple_tp_percent),
					tpOrderType='Limit',
					tpslMode="Partial"
				)
				self.session_bybit.set_trading_stop(
					category="linear",
					symbol=bybit_symbol,
					positionIdx=0,
					slLimitPrice=str(self.cex.price_to_precision(ticker, position['entryPrice'] * (1 + self.sl))),
					stopLoss=str(self.cex.price_to_precision(ticker, position['entryPrice'] * (1 + self.sl))),
					slSize=str(position['contractSize'] * position['contracts']),
					slOrderType='Limit',
					tpslMode="Partial"
				)
				self.session_bybit.set_trading_stop(
					category="linear",
					symbol=bybit_symbol,
					positionIdx=0,
					trailingStop=str(self.cex.price_to_precision(ticker, position['entryPrice']
					                                             * self.trailing_stop_percent)),
					activePrice=str(self.cex.price_to_precision(ticker, position['entryPrice']
					                                            * (1 - self.trailing_trigger_percent))),
				)
			else:
				self.session_bybit.set_trading_stop(
					category="linear",
					symbol=bybit_symbol,
					positionIdx=0,
					tpLimitPrice=str(self.cex.price_to_precision(ticker, position['entryPrice'] * (1 + self.tp))),
					takeProfit=str(self.cex.price_to_precision(ticker, position['entryPrice'] * (1 + self.tp))),
					tpSize=str(position['contractSize'] * position['contracts'] * self.simple_tp_percent),
					tpOrderType='Limit',
					tpslMode="Partial"
				)
				self.session_bybit.set_trading_stop(
					category="linear",
					symbol=bybit_symbol,
					positionIdx=0,
					slLimitPrice=str(self.cex.price_to_precision(ticker, position['entryPrice'] * (1 - self.sl))),
					stopLoss=str(self.cex.price_to_precision(ticker, position['entryPrice'] * (1 - self.sl))),
					slSize=str(position['contractSize'] * position['contracts']),
					slOrderType='Limit',
					tpslMode="Partial"
				)
				self.session_bybit.set_trading_stop(
					category="linear",
					symbol=bybit_symbol,
					positionIdx=0,
					trailingStop=str(self.cex.price_to_precision(ticker, position['entryPrice']
					                                             * self.trailing_stop_percent)),
					activePrice=str(self.cex.price_to_precision(ticker, position['entryPrice']
					                                            * (1 + self.trailing_trigger_percent))),
				)
			return

		avg_price = []
		avg_volume = 0
		side = ''
		for i in orders_ids:
			order = self.cex.fetch_closed_order(i, symbol=ticker)
			side = order['side']
			avg_volume += order['filled']
			avg_price.append(order['average'])
		avg_price = sum(avg_price) / len(avg_price)
		if side == 'sell':
			self.session_bybit.place_order(
				symbol=bybit_symbol,
				category='spot',
				isLeverage=0,
				side='Buy',
				orderType='Limit',
				qty=str(avg_volume),
				price=str(self.cex.price_to_precision(ticker, avg_price * (1 + self.sl))),
				triggerPrice=str(self.cex.price_to_precision(ticker, avg_price * (1 + self.sl))),
				triggerBy='LastPrice',
				orderFilter='StopOrder'
			)
			self.session_bybit.place_order(
				symbol=bybit_symbol,
				category='spot',
				isLeverage=0,
				side='Buy',
				orderType='Limit',
				qty=str(avg_volume),
				price=str(self.cex.price_to_precision(ticker, avg_price * (1 - self.tp))),
				triggerPrice=str(self.cex.price_to_precision(ticker, avg_price * (1 - self.tp))),
				triggerBy='LastPrice',
				orderFilter='StopOrder'
			)
		else:
			self.session_bybit.place_order(
				symbol=bybit_symbol,
				category='spot',
				isLeverage=0,
				side='Sell',
				orderType='Limit',
				qty=str(avg_volume),
				price=str(self.cex.price_to_precision(ticker, avg_price * (1 - self.sl))),
				triggerPrice=str(self.cex.price_to_precision(ticker, avg_price * (1 - self.sl))),
				triggerBy='LastPrice',
				orderFilter='StopOrder'
			)
			self.session_bybit.place_order(
				symbol=bybit_symbol,
				category='spot',
				isLeverage=0,
				side='Sell',
				orderType='Limit',
				qty=str(avg_volume),
				price=str(self.cex.price_to_precision(ticker, avg_price * (1 + self.tp))),
				triggerPrice=str(self.cex.price_to_precision(ticker, avg_price * (1 + self.tp))),
				triggerBy='LastPrice',
				orderFilter='StopOrder'
			)

	@handlers.retry
	def wait_close_one_order(self, ticker, order_ids):
		end = datetime.now() + timedelta(minutes=1)
		while datetime.now() < end:
			closed_orders = self.cex.fetch_closed_orders(ticker, limit=10)
			closed_orders_id = [i['id'] for i in closed_orders]
			closed_order_id = [i for i in order_ids if i in closed_orders_id]
			if closed_order_id:
				return closed_order_id
			time.sleep(0.5)
		return False

	@handlers.retry
	def close_other_orders(self, ticker):
		self.cex.cancel_all_orders(ticker)
