from dataclasses import dataclass
from typing import Union

from price_parser import Price


@dataclass
class Balance:
    x: int
    y: int
    price: Union[Price, None] = None
