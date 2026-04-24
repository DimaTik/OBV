## Start
### Config
1. Перед началом использования бота создайте дубликат config_example.ini
2. Переименуйте дубликат в config.ini 
2. Заполните поля API ключей Bybit
3. Введите токены, которые будут торговаться:
   * BTC/USDT, BTC/USDC - спот
   * BTC/USDT:USDT, BTCPERP (BTCUSDC) - фьючерс
   * BTCUSDT-03MAY26, BTCUSDT-29SEP26 - срочный фьючерс, где дата записана в формате: 
   >ДД.первые три буквы месяца на английском.ГГ
3. Данные индикаторов выставлены по умолчанию, их можно менять
4. Введите желаемые веса для индикаторов
5. Раздел ORDER
   * volume_const - фиксированный объем для сделки, в то случае когда не все индикаторы показывают одно и тоже значение
   * volume_percent - процент от свободных USDT на торговом аккаунте для сделок, когда все индикаторы показывают один и тот же сигнал
   * leverage - кредитное плечо для сделок на фьючерсах, например 10х, 15х, 20х и т.д.

### Docker
#### Установка
Скопируйте и вставьте в консоль по очереди
1. `sudo apt remove $(dpkg --get-selections docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc | cut -f1)`
2. `sudo apt-get update`
3. `sudo apt-get install \
apt-transport-https \
ca-certificates \
curl \
gnupg-agent \
software-properties-common`
4. `curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -`
5. `sudo apt-key fingerprint 0EBFCD88`
6. `sudo add-apt-repository \
"deb [arch=amd64] https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) \
stable"`
7. `sudo apt-get update`
8. `sudo apt-get install docker-ce docker-ce-cli containerd.io`
9. `sudo systemctl start docker`
10.`sudo systemctl status docker`

#### Запуск Бота
Скопируйте и вставьте в консоль по очереди
1. `git clone https://github.com/DimaTik/OBV.git`
2. `cd OBV`
3. `docker build -t bot .` - создание образа bot
4. `docker run --name bot1 -v ${PWD}/config.ini:/app/config.ini bot` - запуск контейнера с именем bot1

#### Просмотр логов
`docker logs bot1`

#### Остановка бота
`docker stop bot1`

#### Удаление бота
`docker rm bot1`
