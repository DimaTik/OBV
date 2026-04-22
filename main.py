import threading
import time

import pandas as pd
import requests
from python_ntfy import NtfyClient

from log import logger
import ex
import handlers
import indicator


def trade(exchange, ticker, side, amount, leverage=None):

	if 'USDC' in ticker:
		balance = exchange.get_balance('USDC')
		balance = f'{balance:.2f} USDC'
	else:
		balance = exchange.get_balance('USDT')
		balance = f'{balance:.2f} USDT'

	logger.info(f'Начал сделку по {ticker} в направлении {side}, баланс = {balance}')
	client.send(f'Начал сделку по {ticker} в направлении {side}, баланс = {balance}')

	if leverage:
		exchange.preparation_derivative(ticker, leverage)

	while True:
		exchange.close_other_orders(ticker)
		orders = exchange.create_orders(ticker, side, amount)
		logger.info(f'Выставленные ордера {ticker}: {orders}')
		closed_order = exchange.wait_close_one_order(ticker, orders)
		if closed_order:
			break

	exchange.close_other_orders(ticker)
	logger.info(f'Закрылся ордер {ticker}: {closed_order}')
	exchange.create_tp_sl(ticker, closed_order, leverage)
	logger.info(f'Выставил TP/SL по {ticker}')

	if 'USDC' in ticker:
		balance = exchange.get_balance('USDC')
		balance = f'{balance:.2f} USDC'
	else:
		balance = exchange.get_balance('USDT')
		balance = f'{balance:.2f} USDT'

	logger.info(f'Сделка по {ticker} совершена. Баланс: {balance}')
	client.send(f'Начал сделку по {ticker} в направлении {side}, баланс = {balance}')


def main():
	config = handlers.ConfigHandler()
	exchange_settings = config.get_exchange_settings()
	proxy_url = config.get_proxy()
	if proxy_url:
		proxies = {
			'http': proxy_url,
			'https': proxy_url
		}
		try:
			test_ip = requests.get('https://api.ipify.org', proxies=proxies, timeout=10).text
			logger.info(f"✅ Внешний IP через прокси: {test_ip}")
		except Exception as e:
			logger.error(f"❌ Не удалось проверить IP через прокси: {e}")
			proxy_url = ''

	user_tickers = config.get_user_tickers()
	indicator_settings = config.get_indicator_settings()
	indicator_weights_settings = config.get_indicator_weights_settings()
	order_settings = config.get_order_settings()
	risk_settings = config.get_risk_management()
	exchange = ex.Exchange(exchange_settings['api_public'], exchange_settings['api_secret'], exchange_settings['mode'],
	                       proxy_url, risk_settings['TP'], risk_settings['SL'], risk_settings['simple_TP_percent'],
	                       risk_settings['trailing_trigger_percent'], risk_settings['trailing_stop_percent'],
	                       order_settings['grid_step_percent'])

	ind = indicator.ObvMacd(indicator_settings['obv_length'], indicator_settings['macd_fast'],
	                        indicator_settings['macd_slow'], indicator_settings['macd_signal'],
	                        indicator_settings['stoch_k'], indicator_settings['stoch_d'],
	                        indicator_settings['stoch_smooth'], indicator_settings['sma_lenght'],
	                        indicator_weights_settings['macd'], indicator_weights_settings['stochastic'],
	                        indicator_weights_settings['obv'], indicator_weights_settings['ma'],
	                        indicator_weights_settings['vol'])

	logger.info(f'Получаю свечи по активам на {indicator_settings['tf']} таймфрейме')
	candles = exchange.get_ohlcv(indicator_settings['tf'], user_tickers)
	res = {}
	for k, v in candles.items():
		if len(v) < 300:
			logger.info(f'Слишком мало свечей для анализа на {k}')
			continue
		df = pd.DataFrame(v, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
		indicators = ind.calculate_indicators(df)
		res[k] = ind.check_signals(indicators)
	for k, v in res.items():
		logger.info(f'{k}: obv: {v[0]}, macd: {v[1]}, stoch: {v[2]}, sma: {v[3]}, vol: {v[4]}, '
		      f'signal: {v[5]}')

	threads = []
	for token, signal in res.items():
		price = exchange.get_price(token)
		if 'USDC' in token:
			balance = exchange.get_balance('USDC')
		else:
			balance = exchange.get_balance('USDT')

		side = signal[-1]
		amount = order_settings['volume_percent'] * balance / price if len([i for i in signal[:-1] if i > 0]) == 5 \
			else order_settings['volume_const']

		if ':' in token:
			pos = exchange.get_position(token)
			if pos is None:
				threads.append(threading.Thread(target=trade, args=(exchange, token, side, amount,
				                                                    order_settings['leverage'],)))
			elif side != pos[0]:
				amount += pos[1]
				threads.append(threading.Thread(target=trade, args=(exchange, token, side, amount,
				                                                    order_settings['leverage'],)))
		else:
			order = exchange.get_last_order(token)
			if order is None:
				threads.append(threading.Thread(target=trade, args=(exchange, token, side, amount,)))
			elif side != order[0]:
				amount += order[1]
				threads.append(threading.Thread(target=trade, args=(exchange, token, side, amount,)))

	if threads:
		logger.info('Совершаю сделки')
		for i in threads:
			i.start()
		for i in threads:
			i.join()
	logger.info('Всё отработал, жду следующую свечу')


if __name__ == '__main__':
	config = handlers.ConfigHandler()
	control_word = config.get_control_word()
	indicator_settings = config.get_indicator_settings()


	timeframe_to_shed = {
		'5m': 300,
		'15m': 900,
		'30m': 1800,
		'1h': 3600,
		'4h': 14400
	}
	client = NtfyClient(topic="eduard_obv_1234")

	logger.info(f'Привет, {control_word}! Я запустился, жду новую свечу, на {indicator_settings['tf']} таймфрейме')
	while True:
		try:
			now = time.time()
			sleep_time = timeframe_to_shed[indicator_settings['tf']] - (now % timeframe_to_shed[indicator_settings['tf']])
			time.sleep(sleep_time)
			main()
		except (KeyboardInterrupt, SystemExit, Exception):
			pass
