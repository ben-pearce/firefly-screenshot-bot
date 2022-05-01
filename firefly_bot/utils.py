import json
import math
import os
from io import IOBase
from typing import Iterable, List

import cv2 as cv
import imagehash
import numpy as np
from PIL import Image
from price_parser import Price
from pytesseract import pytesseract

from firefly_bot.config import config
from firefly_bot.data import Balance


def _get_user_file(user_id: int) -> dict:
    user_file = os.path.join(config.get('bot').get('storage').get('path'), f'{user_id}.json')
    with open(user_file, 'r') as f:
        return json.load(f)


def _write_user_file(user_id: int, obj: dict):
    user_file = os.path.join(config.get('bot').get('storage').get('path'), f'{user_id}.json')
    with open(user_file, 'w') as f:
        json.dump(obj, f)


def _get_similar_accounts_from_screenshot(screenshot: IOBase, accounts: List) -> List:
    diffs = []
    for account in accounts:
        img = Image.open(screenshot)
        image_hash_func = getattr(imagehash, config.get('bot').get('screenshots').get('hash'))
        image_hash = image_hash_func(img)
        original_image_hash = imagehash.ImageHash(np.array(account.get('image').get('hash')))
        diffs.append(image_hash - original_image_hash)

    screenshot.seek(0)
    return [accounts[i]
            for i, diff in enumerate(diffs)
            if diff == min(diffs) and diff < config.get('bot').get('screenshots').get('threshold')]


def _get_nearest_balance_from_screenshot(screenshot: IOBase, x: int, y: int):
    balances = list(_get_balances_from_screenshot(screenshot))
    dists = [math.sqrt(math.pow(b.x - x, 2) + math.pow(b.y - y, 2))
             for b in balances]
    return balances[dists.index(min(dists))]


def _get_balances_from_screenshot(screenshot: IOBase) -> Iterable[Balance]:
    np_bytes = np.asarray(bytearray(screenshot.read()), dtype=np.uint8)
    img = cv.imdecode(np_bytes, cv.IMREAD_GRAYSCALE)

    img_scaled = cv.resize(img, None, fx=2, fy=2)
    ret1, th1 = cv.threshold(img_scaled, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)
    screenshot_data = pytesseract.image_to_data(th1, config='--psm 11', output_type=pytesseract.Output.DICT)

    prices = [Price.fromstring(s) for s in screenshot_data.get('text')]
    potential_balances = [
        Balance(
            screenshot_data['left'][i],
            screenshot_data['top'][i],
            prices[i]
        ) for i in range(len(prices))]

    def empty_price_filter(bal):
        return bal.price.amount is not None and bal.price.currency is not None
    return filter(empty_price_filter, potential_balances)
