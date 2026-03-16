import subprocess

import ex
import handlers


def main():
	user_to_pyne_tf = {
		"10m": "10",
		"15m": "15",
		"30m": "30",
		"1h": "60",
		"4h": "240",
		"1d": "1D"
	}

	config = handlers.ConfigHandler()
	api_key, secret_key = config.get_api()
	indicator_settings = config.get_indicator_settings()
	order_settings = config.get_order_settings()
	exchange = ex.Exchange(api_key, secret_key, order_settings['leverage'], order_settings['volume'])

	tickers = exchange.get_btc_tickers()
	print('Получил данные')
	for ticker in tickers:
		file_name = (f"ccxt_BYBIT_{tickers.replace('/', '_').replace(':', '_')}_"
		             f"{user_to_pyne_tf[indicator_settings['timeframe']]}")
		cmd_load = (f"pyne data download ccxt -s BYBIT:{ticker}"
		            f"-tf {user_to_pyne_tf[indicator_settings['timeframe']]} "
		            f"--from {indicator_settings['period']}")
		subprocess.run(cmd_load, capture_output=True, encoding='utf-8', text=True, shell=True)
		print('Создал файл')

		cmd_analys = (f"pyne run obv_macd_indicator.py "
		              f"--len10 {indicator_settings['obv_length']} "
		              f"--type {indicator_settings['ma_type']} "
		              f"--len {indicator_settings['ma_length']} "
		              f"--slow_length {indicator_settings['macd_slow_length']} "
		              f"--len5 {indicator_settings['len5']} "
		              f"--strat {file_name}.csv "
		              f"{file_name}.ohlcv")
		subprocess.run(cmd_analys, capture_output=True, encoding='utf-8', text=True, shell=True)

		print('Всё')


if __name__ == '__main__':
	main()
