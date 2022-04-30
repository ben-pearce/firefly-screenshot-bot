from dataclasses import dataclass
from io import IOBase
from typing import List

from firefly_iii_client.model.account_read import AccountRead
from imagehash import ImageHash

from firefly_bot.data import Balance


@dataclass
class Setup:
    accounts: List[AccountRead] = None
    chosen_account: AccountRead = None

    screenshot: IOBase = None
    screenshot_hash: ImageHash = None

    balances: List[Balance] = None
    chosen_balance: Balance = None

    sim_accounts: List = None
    relationship: int = None
