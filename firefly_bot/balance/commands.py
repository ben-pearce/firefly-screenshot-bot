import datetime
import logging
from collections import defaultdict
from io import BytesIO
from typing import Union

import firefly_iii_client
import i18n
from firefly_iii_client.api import accounts_api, transactions_api
from firefly_iii_client.model.transaction_split_store import TransactionSplitStore
from firefly_iii_client.model.transaction_store import TransactionStore
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from firefly_bot.balance.data import BalanceUpdate
from firefly_bot.config import config, ff_configuration
from firefly_bot.utils import _get_nearest_balance_from_screenshot, _get_similar_accounts_from_screenshot, \
    _get_user_file

logger = logging.getLogger(__name__)


ACCOUNT, = range(1)


def _update_firefly_balance(account_id: int, balance: float) -> float:
    with firefly_iii_client.ApiClient(ff_configuration) as api_client:
        accounts_instance = accounts_api.AccountsApi(api_client)
        transactions_instance = transactions_api.TransactionsApi(api_client)

        account_record = accounts_instance.get_account(account_id).data

        balance_difference = round(
            balance - float(account_record.attributes.current_balance), 2
        )

        if abs(balance_difference) > 0:
            transaction_store = TransactionStore(
                transactions=[
                    TransactionSplitStore(
                        amount=str(abs(balance_difference)),
                        date=datetime.datetime.now(),
                        description=config.get('bot').get('balance').get('description'),
                        destination_id=None if balance_difference < 0 else str(account_id),
                        source_id=str(account_id) if balance_difference < 0 else None,
                        type="withdrawal" if balance_difference < 0 else "deposit"
                    )
                ]
            )

            try:
                transactions_instance.store_transaction(transaction_store)
            except TypeError as e:
                # Issue with transaction API ?
                logger.error(e)
            logger.info(f"Updated balance of account "
                        f"{account_record.id}:{account_record.attributes.name}")
        else:
            logger.info(f"Balance has remained the same for account "
                        f"{account_record.id}:{account_record.attributes.name}")

        return balance_difference


def _update_firefly_balances_in_relationship(update: Update, context: CallbackContext) -> int:
    balance_update = context.user_data.get('update')
    account_str = ''
    for account in balance_update.sim_accounts:
        logger.info(f"Detected screenshot as balance of account "
                    f"{account.get('id')}:{account.get('name')}")
        balance_update.screenshot.seek(0)
        balance = _get_nearest_balance_from_screenshot(
            balance_update.screenshot, account.get('image').get('x'), account.get('image').get('y')
        )

        balance_difference = _update_firefly_balance(int(account.get('id')), float(balance.price.amount))
        emoji = '📈' if balance_difference > 0 else '📉' if balance_difference < 0 else '⚖'
        account_str += f' - {emoji} {account.get("name")} ' \
                       f'({"+" if balance_difference > 0 else ""}' \
                       f'{balance_difference if balance_difference != 0 else "unchanged"})\n'

    logger.info(f'User {update.effective_user.name}:{update.effective_user.id} '
                f'updated balance of {len(balance_update.sim_accounts)} accounts')
    update.effective_message.reply_markdown(
        i18n.t('balance.balance_updated',
               accounts=account_str,
               count=len(balance_update.sim_accounts)))
    balance_update.screenshot.close()
    del context.user_data['update']
    return ConversationHandler.END


def choose_account_to_update(update: Update, context: CallbackContext) -> int:
    balance_update = context.user_data.get('update')
    query = update.callback_query
    query.answer()

    if query.data == "no":
        balance_update.screenshot.close()
        update.effective_message.reply_text(i18n.t('balance.screenshot_unknown'))
    else:
        balance_update.sim_accounts = [account for account in balance_update.accounts
                                       if account.get('relationship') == int(query.data)]
        try:
            return _update_firefly_balances_in_relationship(update, context)
        except firefly_iii_client.ApiException as e:
            logger.error(e)
            update.effective_message.reply_text(i18n.t('general.firefly_no_connect', reason=e.reason))

        logger.info(f'User {update.effective_user.name}:{update.effective_user.id} chose to '
                    f'update balance for accounts in relationship {query.data}')
    del context.user_data['update']
    return ConversationHandler.END


def update_balance_from_image(update: Update, context: CallbackContext) -> Union[None, int]:
    user = _get_user_file(update.message.from_user.id)

    if 'accounts' not in user:
        return None

    update.message.delete()

    balance_update = BalanceUpdate()
    context.user_data['update'] = balance_update

    logger.info(f'User {update.message.from_user.name}:{update.message.from_user.id} '
                f'submitted screenshot for new balance')

    b = BytesIO()
    screenshot_file = update.message.photo[-1].get_file()
    screenshot_file.download(out=b)

    balance_update.accounts = list(user.get('accounts').values())
    balance_update.screenshot = b
    balance_update.sim_accounts = _get_similar_accounts_from_screenshot(
        balance_update.screenshot,
        balance_update.accounts
    )

    balance_update.screenshot.seek(0)

    if balance_update.sim_accounts and \
        all(balance_update.sim_accounts[0].get('relationship')
            == acc.get('relationship') for acc in balance_update.sim_accounts):
        try:
            return _update_firefly_balances_in_relationship(update, context)
        except firefly_iii_client.ApiException as e:
            logger.error(e)
            update.message.reply_text(i18n.t('general.firefly_no_connect', reason=e.reason))

        balance_update.screenshot.close()
        del context.user_data['update']
        return ConversationHandler.END
    elif len(balance_update.sim_accounts):
        accounts_by_relationship = defaultdict(list)
        for acc in balance_update.sim_accounts:
            accounts_by_relationship[acc.get('relationship')].append(acc)

        keyboard = [[
            InlineKeyboardButton(text=', '.join(acc.get('name') for acc in g), callback_data=r)
        ] for r, g in accounts_by_relationship.items()]
        keyboard.append(
            [InlineKeyboardButton(text=i18n.t('general.collection_none'), callback_data='no')]
        )

        update.message.reply_text(i18n.t('balance.screenshot_conflict'),
                                  reply_markup=InlineKeyboardMarkup(keyboard))
        return ACCOUNT
    else:
        update.message.reply_text(i18n.t('balance.screenshot_unknown'))
        balance_update.screenshot.close()
        del context.user_data['update']
        return ConversationHandler.END


def timeout(update: Update, context: CallbackContext):
    del context.user_data['update']
    logger.info(f'{update.message.from_user.name}:{update.message.from_user.id} timed out balance update')
    return ConversationHandler.END
