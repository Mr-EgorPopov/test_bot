import pyautogui
import time
import random
import pytesseract
from PIL import Image
import keyboard
import re
import sys
import threading
import requests
import tkinter as tk
from tkinter import scrolledtext
from tkinter import simpledialog
import numpy as np
import ctypes
import win32gui
import win32api
import win32ui
import win32con

# Настройка пути к Tesseract OCR (измените, если необходимо)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Координаты и задержки
screen_pribul = (2225, 1527, 2322, 1545)
screen_enemy = (1818, 353, 1969, 387)  # Скрин продавца -1
screen_nickname = (2032, 302, 2127, 322)  # скрин ника
click_update = (2273, 246)  # клик по "обновить"
click_column = (1886, 277)  # клин по колонке
click_redact = (221, 455)  # кнопка редактировать
dclick_coin = (285, 188)  # даблклик по монете
click_all = (439, 361)  # клик по ALL
dclick_mycoin = (34, 186)  # даблклик по товару в рюкзаке
screen_price = (1795, 298, 1968, 330)  # скрин самой "высокой" цены
screen_balance = (605, 919, 740, 946)  # скрин баланса
click_start_sell = (306, 493)  # клик по кнопке "начать продажу"
screen_wait = (408, 413, 547, 429)  # скрин по кнопке "ожидаемая прибыль"

delay_before_click = 0.5   # Задержка перед кликом мышью
delay_after_click = 0.5    # Задержка после клика мышью
delay_mouse = 0.1          # Задержка между нажатием и отпусканием кнопки мыши
stop_sum_file = "stop_sum.json"  # Имя файла для сохранения stop_sum (не используется в текущем коде)
stop_sum = 0  # Переменная для хранения значения stop_sum

# Настройки Telegram
TELEGRAM_BOT_TOKEN = '8137914112:AAEYHuuu_rbL5fhHLQ41DtW2GxZZUJp-aLM'  # Замените на токен вашего бота
TELEGRAM_CHAT_ID = '5268693450'  # Замените на ID вашего чата

# Погрешность для сравнения ников
tolerance = 10
stop_event = threading.Event()  # событие для остановки
read
# Нахождение окна по заголовку
def find_window(title):
    hwnd = 197720
    if hwnd == 0:
        raise Exception(f"Окно с заголовком '{title}' не найдено.")
    return hwnd

# Эмуляция нажатия клавиш
def send_key_to_window(hwnd, key):
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, ord(key), 0)
    time.sleep(0.1)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, ord(key), 0)

# Эмуляция кликов мыши
def click_in_window(hwnd, x, y, button='left'):
    rect = win32gui.GetWindowRect(hwnd)
    window_x, window_y = rect[0], rect[1]
    client_x = x + window_x
    client_y = y + window_y
    lParam = win32api.MAKELONG(client_x, client_y)
    if button == 'left':
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(0.1)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)

def take_screenshot(hwnd, x, y, width, height, filename):
    global Image
    """
    Создает скриншот указанной области в свернутом окне по координатам.
    
    :param hwnd: Дескриптор окна (HWND).
    :param x: Координата X верхнего левого угла области для скриншота.
    :param y: Координата Y верхнего левого угла области для скриншота.
    :param width: Ширина области для скриншота.
    :param height: Высота области для скриншота.
    :return: Объект PIL.Image с изображением.
    """
    # Получаем Device Context (DC) окна
    window_dc = win32gui.GetWindowDC(hwnd)
    mem_dc = win32ui.CreateDCFromHandle(window_dc)
    compatible_dc = mem_dc.CreateCompatibleDC()

    # Создаем bitmap для хранения скриншота
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mem_dc, width, height)
    compatible_dc.SelectObject(bitmap)

    # Копируем содержимое окна в bitmap
    compatible_dc.BitBlt((0, 0), (width, height), mem_dc, (x, y), win32con.SRCCOPY)

    # Преобразуем bitmap в массив байтов
    bmpinfo = bitmap.GetInfo()
    bmpstr = bitmap.GetBitmapBits(True)

    # Создаем объект PIL.Image
    filename = Image.frombuffer(
        'RGB',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRX', 0, 1
    )
    # Освобождаем ресурсы
    win32gui.DeleteObject(bitmap.GetHandle())
    compatible_dc.DeleteDC()
    mem_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, window_dc)

    return filename

def recognize_sum():
    """
     Распознает число (цену) на скриншоте с помощью Tesseract OCR.
     Returns:
        int: Распознанная сумма или 0 при ошибке.
    """
    try:
        image = Image.open('price.png')
        image = image.resize((328, 62))  # Изменение размера изображения
        path_to_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        pytesseract.pytesseract.tesseract_cmd = path_to_tesseract
        text = pytesseract.image_to_string(image, config='digit', lang='rus')  # Распознаем текст из картинки с параметрами digit и rus
        text = text.replace('мпн', 'млн')  # Заменяем мпн на млн
        text = text.replace('мл', 'млн')  # Заменяем мл на млн
        mln = 0
        if 'млн' in text:  # Если в строке есть млн
            mln = text.split(' млн')[0]  # Забираем значение до млн
        if ' ' in mln:
            mln = text.split(' ')[1]  # Забираем значение после пробела
        tsh = 0
        if 'тыс' in text:  # Если есть тыс
            tsh = text.split(' тыс')[0]  # Забираем значение до тыс
        if ' ' in tsh:
            tsh = tsh.split(' ')  # Если есть пробел
            n = len(tsh)
            tsh = tsh[n - 1]  # Забираем значение после пробела
        eden = 0
        if 'аден' in text:  # Если есть аден
            eden = text.split(' аден')[0]  # Забираем значение до аден
        if ' ' in eden:
            eden = eden.split(' ')  # Если есть пробел
            n = len(eden)
            eden = eden[n - 1]  # Забираем значение после пробела
        mln = int(1) * 1000000  # млн всегда 1
        tsh = int(tsh) * 1000 if tsh else 0  # Если нет тыс, то 0, если есть то множим на 1000
        if eden == 'тыс' or eden == 'млн':
            eden = 0  # Если eden это тыс, или млн, то это 0
        else:
            eden = int(eden) if eden else 0  # Если есть значение, то забираем, если нет то 0
        rez = str(mln + tsh + eden)  # Складываем полученное значение
        return int(rez)
    except Exception as e:
        print(f"Ошибка распознавания текста: {e}")
        return 0

def recognize_sum_balance(image):
    """
    Распознает баланс на скриншоте с помощью Tesseract OCR.
    Args:
        image (PIL.Image.Image): Изображение для распознавания.
    Returns:
        int: Распознанный баланс или 0 при ошибке.
    """
    try:
        image = image.resize((328, 62))
        text = pytesseract.image_to_string(image, config='digit', lang='rus')  # Пытаемся распознать текст как одно слово.
        text = ''.join(re.findall(r'\d', text))  # Убираем все кроме цифр
        return int(text) if text else 0
    except Exception as e:
        print(f"Ошибка распознавания текста: {e}")
        return 0

def recognize_balance(image):
    """
    Распознает баланс на скриншоте с помощью Tesseract OCR.
    Args:
        image (PIL.Image.Image): Изображение для распознавания.
    Returns:
        int: Распознанный баланс или 0 при ошибке.
    """
    try:
        image = image.resize((328, 62))
        text = pytesseract.image_to_string(image, config='--psm 6 --oem 3', lang='rus')
        text = ''.join(re.findall(r'\d', text))
        return int(text) if text else 0
    except Exception as e:
        print(f"Ошибка распознавания текста: {e}")
        return 0

def click(hwnd, x, y, button='left'):
    rect = win32gui.GetWindowRect(hwnd)
    window_x, window_y = rect[0], rect[1]
    client_x = x + window_x
    client_y = y + window_y
    lParam = win32api.MAKELONG(client_x, client_y)
    if button == 'left':
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(0.1)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)

def double_click(hwnd, x, y, button='left'):
    rect = win32gui.GetWindowRect(hwnd)
    window_x, window_y = rect[0], rect[1]
    client_x = x + window_x
    client_y = y + window_y
    lParam = win32api.MAKELONG(client_x, client_y)
    if button == 'left':
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(0.1)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        time.sleep(0.1)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(0.1)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        time.sleep(0.1)

def type_text(hwnd, text):
    for char in text:
        send_key_to_window(hwnd, char)
        time.sleep(0.1)

def check_balance_and_notify(added_sum):
    """
    Проверяет, достаточно ли прибыль и при необходимости отправляет уведомление в Telegram.
    Returns:
        bool: True если прибыль недостаточна, и нужно отправлять уведомление, False если достаточно.
    """
    try:
        screenshot4_path = take_screenshot(hwnd, screen_balance[0], screen_balance[1], 135, 27,
                                           "balance.png")
        sum2 = recognize_sum_balance(Image.open(screenshot4_path))
        print(f"Остаток адены: {sum2}")
        if sum2 < 3000000000:
            try:
                send_telegram_message(
                    f"🔥🔥🔥ВСЕ CКУПИЛ🔥🔥🔥")
                time.sleep(3)
                send_telegram_message(
                    f"🔥🔥🔥ПОСЛЕДНЯЯ ЦЕНА: {added_sum}🔥🔥🔥")
                return True  # Возвращаем True, так как условие выполнилось
            except Exception as e:
                print(f"Ошибка при отправке уведомления о sum2: {e}")
                return False  # Возвращаем False, так как условие не выполнилось
    except Exception as e:
        print(f"Ошибка при выполнении проверки sum2: {e}")
        return False

def load_stop_sum():
    """ Запрашивает у пользователя значение stop_sum через консоль. """
    global stop_sum
    while True:
        print(f"//------------------------------МЫ НАЧАЛИ СО 156 МЛРД------------------------------//")
        stop_sum_input = input("Введите значение stop_sum: ")
        if stop_sum_input.strip() == "":
            print("Значение stop_sum не может быть пустым. Пожалуйста, введите значение.")
            continue
        try:
            stop_sum = int(stop_sum_input)
            print(f"Используется значение stop_sum: {stop_sum}")
            break
        except ValueError:
            print("Некорректный ввод. Пожалуйста, введите целое число.")

def load_wait_duration():
    """ Запрашивает у пользователя значение wait_duration через консоль. """
    global wait_duration
    while True:
        wait_duration_input = input("Введите 1 для фиксированной задержки (70 сек)\nВведите 2 для случайной задержки (70-180 сек): ")
        if wait_duration_input.strip() == "":
            print("Значение wait_duration не может быть пустым. Пожалуйста, введите значение.")
            continue
        try:
            wait_duration_choice = int(wait_duration_input)
            if wait_duration_choice == 1:
                wait_duration = 70
                print(f"Используется фиксированная задержка: {wait_duration} сек")
                break
            elif wait_duration_choice == 2:
                wait_duration = random.randint(70, 180)
                print(f"Используется случайная задержка: {wait_duration} сек")
                break
            else:
                print("Некорректный ввод. Пожалуйста, введите 1 или 2.")
        except ValueError:
            print("Некорректный ввод. Пожалуйста, введите целое число.")

def send_telegram_message(message):
    """
    Отправляет сообщение в Telegram.
    Args:
        message (str): Текст сообщения.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        print(f"Telegram message sent successfully! Response code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")

def compare_screenshots(img1, img2, tolerance):
    """
    Сравнивает два изображения на схожесть.
    Args:
        img1 (PIL.Image.Image): Первое изображение.
        img2 (PIL.Image.Image): Второе изображение.
        tolerance (int): Допустимое различие между пикселями.
    Returns:
        bool: True, если изображения схожи, иначе False.
    """
    try:
        img1_array = np.array(img1)  # Конвертируем в массив
        img2_array = np.array(img2)  # Конвертируем в массив
        if img1_array.shape != img2_array.shape:  # Если размерности разные
            return False
        diff = np.abs(img1_array.astype(int) - img2_array.astype(int))  # Вычитаем массивы
        return np.max(diff) <= tolerance  # Проверяем на максимальную погрешность
    except Exception as e:
        print(f"Ошибка при сравнении скриншотов: {e}")
        return False

def round_down_to_nearest_10(number):
    """
    Округляет число до ближайшего меньшего числа, кратного 10.
    Args:
        number (int): Число для округления.
    Returns:
        int: Округленное число.
    """
    return number - (number % 10)

def process_actions():
    """
      Основной цикл автоматизации действий в игре.
      Выполняет клики, распознавание текста, сравнение изображений, и отправляет уведомления.
    """
    global stop_sum, first_screenshot, stop_event  # Указываем, что используется глобальная переменная
    step = 0  # Задаем начальное значение шага
    first_screenshot_taken = False  # Указываем, что первый скриншот еще не сделан
    first_screenshot = None
    added_sum = 0
    sum1 = 0  # инициализируем sum1
    screenshot5_path = take_screenshot(hwnd, screen_price[0], screen_price[1], 173, 32,
                                       "price_enemy.png")  # Создаем скриншот цены конкурента
    Image.open(screenshot5_path).save('price.png')  # Сохраняем скриншот
    sum16 = recognize_sum()  # Распознаем сумму
    added_sum = sum16
    while not stop_event.is_set():
        if not first_screenshot_taken:
            try:
                screenshot1_path = take_screenshot(hwnd, screen_nickname[0], screen_nickname[1], 95,
                                                   20,
                                                   "nickname.png")  # Создаем скриншот ника и сохраняем
                first_screenshot = Image.open(screenshot1_path)  # Открываем скриншот
                first_screenshot_taken = True  # Указываем, что первый скриншот был сделан
            except Exception as e:
                print(f"Ошибка при загрузке first_screenshot: {e}")
                break
        if step == 0:
            step += 1  # Увеличиваем шаг на 1
            time.sleep(0.1)  # Короткая задержка
        elif step == 1:
            # 2-7 Пункты.
            if check_balance_and_notify(added_sum):  # если баланс мал, то завершаем работу
                break  # Выходим из цикла
            click(hwnd, click_update[0], click_update[1], button='left')  # Кликаем на "Обновить"
            time.sleep(1)  # Ожидание 1 сек
            click(hwnd, click_column[0], click_column[1], button='left')  # Кликаем на колонку
            time.sleep(0.4)  # Ожидание 0.4 сек
            click(hwnd, click_column[0], click_column[1], button='left')  # Кликаем на колонку еще раз
            time.sleep(0.4)  # Ожидание 0.4 сек
            step += 1  # Увеличиваем шаг на 1
            time.sleep(0.1)  # Короткая задержка
        elif step == 2:
            # 8. скрин и сравнение.
            screenshot2_path = take_screenshot(hwnd, screen_nickname[0], screen_nickname[1], 95,
                                                   20,
                                                   "nickname.png")  # Создаем скриншот ника
            try:
                img2 = Image.open(screenshot2_path)  # Открываем скриншот ника
                if compare_screenshots(first_screenshot, img2, tolerance):  # Если ники не отличаются, то пропускаем и идем в конец
                    step = 7  # Указываем шаг 7
                    continue  # Проверка на большую разницу с ценой конкурента
            except Exception as e:
                print(f"Ошибка при сравнении скриншотов: {e}")
            step += 1  # Увеличиваем шаг на 1
            time.sleep(0.1)  # Короткая задержка
        elif step == 3:
            screenshot3_path = take_screenshot(hwnd, screen_price[0], screen_price[1], 173,
                                               32,
                                               "cenapricecurenta.png")  # Создаем скриншот цены
            Image.open(screenshot3_path).save('price.png')  # Сохраняем скриншот
            sum1 = recognize_sum()  # Считываем сумму
            print(f"Первая цена: {sum1}")
            added_sum = sum1 + random.choice([1, 2, 5, 10, 20])  # Уменьшаем цену на случайное значение  # Округляем значение до ближайшего меньшего числа, кратного 10
            print(f"Вводимая цена: {added_sum}")
            if added_sum >= stop_sum:  # Если цена ниже стоп-суммы
                print("Цена выше порога.")
                try:
                    send_telegram_message(
                        f"❌❌ВЫШЕ ГРАНИЦЫ❌❌")  # Отправляем сообщение в телеграм
                    time.sleep(2)
                    send_telegram_message(
                        f"❌❌ВЫШЕ ГРАНИЦЫ❌❌")  # Отправляем сообщение в телеграм
                    time.sleep(2)
                except Exception as e:
                    print(f"Ошибка при отправке сообщения Telegram: {e}")
                wait_time = 0
                print(f"Ожидание {wait_duration} секунд...")
                while wait_time < wait_duration and not stop_event.is_set():  # check if stop
                    time.sleep(1)
                    wait_time += 1
                if stop_event.is_set():
                    break
                step = 0  # Сбрасываем шаг до 0
                continue
            print("Фиксим.")
            # Вторая ветка
            click(hwnd, click_redact[0], click_redact[1], button='left')  # Кликаем на редактировать
            time.sleep(2)  # Ожидание 2 сек
            double_click(hwnd, dclick_coin[0], dclick_coin[1], button='left')  # Двойной клик по монете
            time.sleep(1.5)  # Ожидание 1.5 сек
            click(hwnd, click_all[0], click_all[1], button='left')  # Кликаем на "Все"
            time.sleep(0.8)  # Ожидание 0.8 сек
            send_key_to_window(hwnd, win32con.VK_RETURN)  # Нажимаем ентер
            time.sleep(0.8)  # Ожидание 0.8 сек
            double_click(hwnd, dclick_mycoin[0], dclick_mycoin[1], button='left')  # Двойной клик по моему товару
            time.sleep(1)  # Ожидание 1 сек
            step += 1  # Увеличиваем шаг на 1
            time.sleep(0.1)  # Короткая задержка
        elif step == 4:
            type_text(hwnd, added_sum)  # Печатаем цену
            time.sleep(0.5)  # Ожидание 0.5 сек
            send_key_to_window(hwnd, win32con.VK_RETURN)  # Нажимаем ентер
            step += 1  # Увеличиваем шаг на 1
            time.sleep(0.1)  # Короткая задержка
            screenshot4_path = take_screenshot(hwnd, screen_balance[0], screen_balance[1], 135, 27,
                                           "bal.png")
            sum19 = recognize_sum_balance(Image.open(screenshot4_path))
            finally_volume = (sum19 // added_sum)
            type_text(hwnd, finally_volume)  # Печатаем цену
            time.sleep(0.8)  # Ожидание 0.8 сек
            send_key_to_window(hwnd, win32con.VK_RETURN)  # Нажимаем ентер
            time.sleep(1.5)  # Ожидание 1.5 сек
            step += 1  # Увеличиваем шаг на 1
            time.sleep(0.1)  # Короткая задержка
        elif step == 6:
            # Пункт 15
            click(hwnd, click_start_sell[0], click_start_sell[1], button='left')  # Кликаем на "Начать продажу"
            wait_time = 0
            print(f"Ожидание {wait_duration} секунд...")
            while wait_time < wait_duration and not stop_event.is_set():
                time.sleep(1)
                wait_time += 1
            if stop_event.is_set():
                break
            step = 0  # Сбрасываем шаг до 0
            continue  # Идем в начало
        elif step == 7:
            # Если большая разница в цене с конкурентом
            screenshot4_path = take_screenshot(hwnd, screen_enemy[0], screen_enemy[1], 151,
                                               34,
                                               "price_nick.png")  # Создаем скриншот ника продавца
            Image.open(screenshot4_path).save('price.png')  # Сохраняем скриншот
            sum12 = recognize_sum()  # Распознаем сумму
            screenshot5_path = take_screenshot(hwnd, screen_price[0], screen_price[1], 173,
                                               32,
                                               "price_enemy.png")  # Создаем скриншот цены конкурента
            Image.open(screenshot5_path).save('price.png')  # Сохраняем скриншот
            sum11 = recognize_sum()  # Распознаем сумму
            print(f"Моя цена: {sum11}")
            print(f"Цена за мной: {sum12}")
            if (sum11 - sum12) > 40:  # Если разница между нашими ценами и конкурентами > 40
                added_sum = sum12 + random.choice([1, 2, 5, 10, 20])  # Уменьшаем цену на рандомное значение
                if added_sum >= stop_sum:  # Если сумма ниже стоп суммы
                    print("Сумма достигла предела, скрипт завершен.")
                    try:
                        send_telegram_message(
                            f"❌❌ВЫШЕ ГРАНИЦЫ❌❌")  # Отправляем сообщение в телеграм
                        time.sleep(2)
                        send_telegram_message(
                            f"❌❌ВЫШЕ ГРАНИЦЫ❌❌")  # Отправляем сообщение в телеграм
                        time.sleep(2)
                    except Exception as e:
                        print(f"Ошибка при отправке сообщения Telegram: {e}")
                    wait_time = 0
                    print(f"Ожидание {wait_duration} секунд...")
                    while wait_time < wait_duration and not stop_event.is_set():
                        time.sleep(1)
                        wait_time += 1
                    if stop_event.is_set():
                        break
                    step = 0  # Сбрасываем шаг до 0
                    continue  # Идем в начало
                print("Корректирую разницу с конкурентом")
                # Вторая ветка
                click(hwnd, click_redact[0], click_redact[1], button='left')  # Кликаем на редактировать
                time.sleep(2)  # Ждем 2 сек
                double_click(hwnd, dclick_coin[0], dclick_coin[1], button='left')  # Двойной клик на монету
                time.sleep(1.5)  # Ждем 1.5 сек
                click(hwnd, click_all[0], click_all[1], button='left')  # Кликаем на "Все"
                time.sleep(0.8)  # Ждем 0.8 сек
                send_key_to_window(hwnd, win32con.VK_RETURN)  # Нажимаем ентер
                time.sleep(0.8)  # Ждем 0.8 сек
                double_click(hwnd, dclick_mycoin[0], dclick_mycoin[1], button='left')  # Двойной клик на мой товар
                time.sleep(1)  # Ждем 1 сек
                time.sleep(0.1)  # Короткая задержка
                # Пункты 6-10
                type_text(hwnd, added_sum)  # Печатаем цену
                time.sleep(0.5)  # Ждем 0.5 сек
                send_key_to_window(hwnd, win32con.VK_RETURN)  # Нажимаем ентер
                time.sleep(0.1)  # Короткая задержка
                screenshot4_path = take_screenshot(hwnd, screen_balance[0], screen_balance[1], 135, 27,
                                           "balance.png")
                sum19 = recognize_sum_balance(Image.open(screenshot4_path))
                finally_volume = (sum19 // added_sum)
                type_text(hwnd, finally_volume)  # Печатаем цену
                time.sleep(0.8)  # Ждем 0.8 сек
                send_key_to_window(hwnd, win32con.VK_RETURN)  # Нажимаем ентер
                time.sleep(1.5)  # Ждем 1.5 сек
                # Пункт 15
                click(hwnd, click_start_sell[0], click_start_sell[1], button='left')  # Кликаем на "Начать продажу"
                wait_time = 0
                print(f"Ожидание {wait_duration} секунд...")
                while wait_time < wait_duration and not stop_event.is_set():
                    time.sleep(1)
                    wait_time += 1
                if stop_event.is_set():
                    break
                step = 0  # Сбрасываем шаг до 0
                continue  # Идем в начало
            else:
                print("Все ок.")
                added_sum = sum11
                wait_time = 0
                print(f"Ожидание {wait_duration} секунд...")
                while wait_time < wait_duration and not stop_event.is_set():
                    time.sleep(1)
                    wait_time += 1
                if stop_event.is_set():
                    break
                step = 0  # Сбрасываем шаг до 0
                continue  # Идем в начало

def start_script():
    """
     Запускает основной цикл автоматизации.
     Также запускает поток для проверки баланса и отправки уведомления(закоментировано).
    """
    global stop_event
    stop_event.clear()  # Сбрасываем флаг остановки перед запуском
    process_actions()
    print("///    PAUSE    ///")  # Сообщение о паузе

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Сворачиваем окно при запуске
    try:
        while True:
            hwnd = find_window("Lineage II")  # Замените на точное название окна
            load_stop_sum()  # Загружаем значение стоп суммы
            # Запрос значения wait_duration
            load_wait_duration()
            keyboard.add_hotkey('f9', lambda: stop_event.set())
            keyboard.wait('f10')  # ожидаем нажатие f10
            start_script()  # Запускаем скрипт
    except KeyboardInterrupt:
        print("\nСкрипт остановлен пользователем (Ctrl+C).")
    except Exception as e:
        print(f"Ошибка: {e}")  # Выводим ошибку
    finally:
        keyboard.unhook_all_hotkeys()
    root.mainloop()  # Запускаем GUI
