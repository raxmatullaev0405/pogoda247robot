#Импортируем нужные модули
import json
import requests
import time
import urllib 
import logging
import signal
import sys

#Переменные для получение и отправка данные через TelegramApi и OpenWeatherApi
TOKEN = "1837051950:AAGOaQ9da5B_TqbZt824FrgOPH5Np0KnuiQ"
OWM_KEY = "0fd7b382242dd8d15aa95115e419b2da"
POLLING_TIMEOUT = None
#Функция для анализа обновлений из TelegramApi
def getText(update):            return update["message"]["text"]
def getLocation(update):        return update["message"]["location"]
def getChatId(update):          return update["message"]["chat"]["id"]
def getUpId(update):            return int(update["update_id"])
def getResult(updates):         return updates["result"]

#Функция для анализа погодных откликов OpenWeatherApi
def getDesc(w):                 return w["weather"][0]["description"]
def getTemp(w):                 return w["main"]["temp"]
def getCity(w):                 return w["name"]
#присваем переменные для logger и установливаем статус debug
logger = logging.getLogger("weather-telegram")
logger.setLevel(logging.DEBUG)

#Города для запроса погоды, те города в меню бота
cities = ["Москва", "Королев", "Ташкент", "Коканд"]
def sigHandler(signal, frame):
    logger.info("Сигнал входа Получен. Завершения скрипта... Пока-Пока")
    sys.exit(0)
    #Настройка ведения журнала файлов и консоли
def configLogging():
    #Создадим регистратор журнала файлов и установит уровень для отладки DEBUG
    #Режим = запись -> Очистка существующий файл журнала логов
    handler = logging.FileHandler("run.log", mode="w")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #Создайим обработчик консоли и установит уровень для отладки в INFO
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(levelname)s] - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def parseConfig():
    global URL, URL_OWM, POLLING_TIMEOUT
    URL = "https://api.telegram.org/bot{}/".format(TOKEN)
    URL_OWM = "http://api.openweathermap.org/data/2.5/weather?appid={}&units=metric&lang=ru".format(OWM_KEY)
    POLLING_TIMEOUT
    
    #Отправлаем запрос к Telegram-боту и получим ответ JSON формате и кодировка UTF-8
def makeRequest(url):
    logger.debug("URL: %s" % url)
    r = requests.get(url)
    resp = json.loads(r.content.decode("utf8"))
    return resp

#Вернем все обновления с идентификатором > смещение данные
#(Список обновлененный данные хранится в Telegram, в течение 24 часов)
def getUpdates(offset=None):
    url = URL + "getUpdates?timeout=%s" % POLLING_TIMEOUT
    logger.info("Получение обновлений") 
    if offset:
        url += "&offset={}".format(offset)
    js = makeRequest(url)
    return js

#Создайте виртаулную кнопку-клавиша для экранных опций Telegram бота
def buildKeyboard(items):
    keyboard = [[{"text":item}] for item in items]
    replyKeyboard = {"keyboard":keyboard, "one_time_keyboard": True}
    logger.debug(replyKeyboard)
    return json.dumps(replyKeyboard)

def buildCitiesKeyboard():
    keyboard = [[{"text": c}] for c in cities]
    keyboard.append([{"text": "Поделиться местоположением", "request_location": True}])
    replyKeyboard = {"keyboard": keyboard, "one_time_keyboard": True}
    logger.debug(replyKeyboard)
    return json.dumps(replyKeyboard)
    # Отправляем запрос к OpenWeatherApi о погоде для места или координат полученный от пользвателя
def getWeather(place):
    if isinstance(place, dict):     #Предоставлены координаты
        lat, lon = place["latitude"], place["longitude"]
        url = URL_OWM + "&lat=%f&lon=%f&cnt=1" % (lat, lon)
        logger.info("Запрашиваю погоду: " + url)
        js = makeRequest(url)
        logger.debug(js)
        return u"%s \N{DEGREE SIGN}C, %s в городе %s" % (getTemp(js), getDesc(js), getCity(js))
    else:                           #предоставленное название места - те города
        #отправляем запрос
        url = URL_OWM + "&q={}".format(place)
        logger.info("Запрашиваю погоду: " + url)
        js = makeRequest(url)
        logger.debug(js)
        return u"%s \N{DEGREE SIGN}C, %s в городе %s" % (getTemp(js), getDesc(js), getCity(js))

#Отправить сообщение на идентификатор чата пользвателя
def sendMessage(text, chatId, interface=None):
    text = text.encode('utf-8', 'strict')                                                       
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chatId)
    if interface:
        url += "&reply_markup={}".format(interface)
    requests.get(url)

#Получить идентификатор последнего доступного обновления
def getLastUpdateId(updates):
    ids = []
    for update in getResult(updates):
        ids.append(getUpId(update))
    return max(ids)
    # Следим за состояниями разговора диалога пользвателя: "Запрашиваю погоду"
chats = {}

#Ech-Callback функция для получение обратных сообщении
def handleUpdates(updates):
    for update in getResult(updates):
        chatId = getChatId(update)
        try:
            text = getText(update)
        except Exception as e:
            logger.error("На текстовом поле не указан местоположение для обновления данных.Попытайтемся узнать местоположение")
            loc = getLocation(update)
            #Была ли ранее запрошена погода?
            if (chatId in chats) and (chats[chatId] == "weatherReq"):
                logger.info("Погода, запрошенная для %s в чате id %d" % (str(loc), chatId))
                #Отправить погоду в идентификатор чата пользвателя и очистить состояние данные
                sendMessage(getWeather(loc), chatId)
                del chats[chatId]
            continue

        if text == "/pogoda":
            keyboard = buildCitiesKeyboard()
            chats[chatId] = "weatherReq"
            sendMessage("Выберите город:", chatId, keyboard)
        elif text == "/start":
            sendMessage("Аксиома Кана: Когда все остальное терпит неудачу, прочитайте инструкции", chatId)
        elif text.startswith("/"):
            logger.warning("Неверная команда %s" % text)    
            continue
        elif (text in cities) and (chatId in chats) and (chats[chatId] == "weatherReq"):
            logger.info("Weather requested for %s" % text)
            # Send weather to chat id and clear state
            sendMessage(getWeather(text), chatId)
            del chats[chatId]
        else:
            keyboard = buildKeyboard(["/pogoda"])
            sendMessage("Я каждый день узнаю что-то новое, но пока вы можете спросить меня о погоде.", chatId, keyboard)

def main():
    #Настройка регистров файла лога и консолных данные
    configLogging()

    #Получаем токены и ключи данных Api
    parseConfig()
 
    # Intercept Ctrl-C SIGINT 
    signal.signal(signal.SIGINT, sigHandler) 
 
    #main-функция для цикла
    last_update_id = None
    while True:
        updates = getUpdates(last_update_id)
        if len(getResult(updates)) > 0:
            last_update_id = getLastUpdateId(updates) + 1
            handleUpdates(updates)
        time.sleep(0.5)

if __name__ == "__main__":
    main()