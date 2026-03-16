import ccxt

import handlers


class Exchange:
	def __init__(self, api_key, api_secret, leverage, volume):
		self.api_key = api_key
		self.api_secret = api_secret
		self.leverage = leverage
		self.volume = volume
		self.api_params = {
			"apiKey": self.api_key,
			"secret": self.api_secret,
			"enableRateLimit": True
		}
		self.cex = ccxt.bybit(self.api_params)

	@handlers.retry
	def get_btc_tickers(self):
		tickers = self.cex.fetch_markets()
		tickers = [i['symbol'] for i in tickers if (i['symbol'][:8] == 'BTC/USDT' and i['symbol'][-1] not in ('P', 'C'))
		           or i['symbol'][:8] == 'BTC/USDC']
		return tickers

	@handlers.retry
	def create_orders(self):
		pass

	@handlers.retry
	def cancel_orders(self, order_id):
		pass
