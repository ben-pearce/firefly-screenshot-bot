from dataclasses import dataclass
from io import IOBase
from typing import Dict, List


@dataclass
class BalanceUpdate:
    screenshot: IOBase = None

    accounts: List[Dict] = None
    sim_accounts: List[Dict] = None
