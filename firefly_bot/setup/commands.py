import logging
import os
from collections import defaultdict
from io import BytesIO

import firefly_iii_client
import i18n
import imagehash
from PIL import Image
from firefly_iii_client.api import accounts_api
from firefly_iii_client.model.account_type_filter import AccountTypeFilter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from firefly_bot.config import config, ff_configuration
from firefly_bot.setup.data import Setup
from firefly_bot.utils import _get_balances_from_screenshot, _get_similar_accounts_from_screenshot, _get_user_file, \
    _write_user_file

ACCOUNT, EXAMPLE, BALANCE, RELATED, CONFIRM = range(5)

logger = logging.getLogger(__name__)


def account(update: Update, context: CallbackContext) -> int:
    user_file = os.path.join(config.get('bot').get('storage').get('path'), f'{update.message.from_user.id}.json')
    if not os.path.exists(user_file):
        logger.info(f"{update.effective_user.name}:{update.effective_user.id} tried starting "
                    f"setup before account registration")
        update.message.reply_text(i18n.t('setup.user_file_missing'))
        return ConversationHandler.END

    logger.info(f"{update.effective_user.name}:{update.effective_user.id} is starting setup")

    setup = Setup()
    context.user_data['setup'] = setup

    user = _get_user_file(update.message.from_user.id)
    accounts = user.get('accounts', dict())

    with firefly_iii_client.ApiClient(ff_configuration) as api_client:
        api_instance = accounts_api.AccountsApi(api_client)

        try:
            api_response = api_instance.list_account(type=AccountTypeFilter('asset'))
            setup.accounts = api_response.data

            keyboard = []
            for i, account_record in enumerate(api_response.data):
                if account_record.id not in accounts:
                    acc = account_record.attributes
                    keyboard.append([InlineKeyboardButton(
                        text=acc.name,
                        callback_data=i
                    )])

            logger.info(f"Found {len(setup.accounts)} asset accounts from FireflyIIAPI")

            update.message.reply_text(i18n.t('setup.which_account'), reply_markup=InlineKeyboardMarkup(keyboard))

            return ACCOUNT
        except firefly_iii_client.ApiException as e:
            logger.warning(f"Couldn't connect to FireflyIIAPI: {e}")
            update.message.reply_text(i18n.t('general.firefly_no_connect', reason=e.reason))
            return ConversationHandler.END


def account_chosen(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    setup = context.user_data.get('setup')
    setup.chosen_account = setup.accounts[int(query.data)]

    query.message.reply_markdown(i18n.t('setup.account_setup_begin', name=setup.chosen_account.attributes.name))

    logger.info(f"{query.from_user.name}:{query.from_user.id} is "
                f"configuring an account {setup.chosen_account.attributes.name}:{setup.chosen_account.id}")
    return EXAMPLE


def example(update: Update, context: CallbackContext) -> int:
    setup = context.user_data.get('setup')
    user = _get_user_file(update.message.from_user.id)
    update.message.delete()

    with BytesIO() as b:
        screenshot_file = update.message.photo[-1].get_file()
        screenshot_file.download(out=b)
        b.seek(0)

        img = Image.open(b)
        image_hash_func = getattr(imagehash, config.get('bot').get('screenshots').get('hash'))
        setup.screenshot = b
        setup.screenshot_hash = image_hash_func(img)

        b.seek(0)
        balances = list(_get_balances_from_screenshot(b))

        b.seek(0)
        accounts = list(user.get('accounts', dict()).values())
        setup.sim_accounts = _get_similar_accounts_from_screenshot(b, accounts)

        logger.info(f"{update.effective_user.name}:{update.effective_user.id} submitted screenshot for setup: {img}, "
                    f"found {len(balances)} balances, "
                    f"found {len(setup.sim_accounts)} accounts with similar image hashes")
    if not balances:
        update.message.reply_text(i18n.t('setup.example_no_balance'))
        logger.warning(f"Found NO balances, maintaining state...")
        return EXAMPLE
    elif len(balances) == 1:
        setup.chosen_balance = balances.pop()
        logger.info(f"Found only a single balance, passing...")
        return _check_relationships(update, context)
    else:
        setup.balances = balances
        logger.info(f"Found {len(balances)} potential balances for account "
                    f"{setup.chosen_account.attributes.name}:{setup.chosen_account.id}")
        keyboard = [[InlineKeyboardButton(
                text=f"{bal.price.currency}{bal.price.amount:,.2f}",
                callback_data=i
            )] for i, bal in enumerate(balances)]

        update.message.reply_markdown(
            i18n.t('setup.example_balance_found', name=setup.chosen_account.attributes.name),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return BALANCE


def balance_chosen(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    setup = context.user_data.get('setup')
    setup.chosen_balance = setup.balances[int(query.data)]
    logger.info(f"{update.effective_user.name}:{update.effective_user.id} selected balance for "
                f"{setup.chosen_account.attributes.name}:{setup.chosen_account.id}")
    return _check_relationships(update, context)


def relation_chosen(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    setup = context.user_data.get('setup')

    if query.data == 'no':
        logger.info(f'{query.from_user.name}:{query.from_user.id} chose no relationship')
    else:
        setup.relationship = int(query.data)
        logger.info(f'{query.from_user.name}:{query.from_user.id} chose relationship {query.data}')
    return _request_confirm(update, context)


def _check_relationships(update: Update, context: CallbackContext) -> int:
    setup = context.user_data.get('setup')

    if len(setup.sim_accounts) > 0:
        accounts_by_relationship = defaultdict(list)
        for acc in setup.sim_accounts:
            accounts_by_relationship[acc.get('relationship')].append(acc)

        keyboard = [[
            InlineKeyboardButton(text=', '.join(acc.get('name') for acc in g), callback_data=r)
        ] for r, g in accounts_by_relationship.items()]
        keyboard.append(
            [InlineKeyboardButton(text=i18n.t('general.collection_none'), callback_data='no')]
        )
        update.effective_message.reply_markdown(
            i18n.t('setup.relationship_opportunity'),
            reply_markup=InlineKeyboardMarkup(keyboard))
        return RELATED
    else:
        return _request_confirm(update, context)


def _request_confirm(update: Update, context: CallbackContext) -> int:
    setup = context.user_data.get('setup')

    keyboard = [
        InlineKeyboardButton(text=i18n.t('general.confirm'), callback_data="1"),
        InlineKeyboardButton(text=i18n.t('general.cancel'), callback_data="0")
    ]
    update.effective_message.reply_markdown(
        i18n.t('setup.setup_confirm',
               id=setup.chosen_account.id,
               name=setup.chosen_account.attributes.name,
               x=setup.chosen_balance.x,
               y=setup.chosen_balance.y),
        reply_markup=InlineKeyboardMarkup([keyboard]))
    return CONFIRM


def confirm(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    setup = context.user_data.get('setup')
    del context.user_data['setup']

    if query.data == "1":
        user = _get_user_file(query.from_user.id)
        accounts = user.get('accounts', dict())
        relationship = user.get('relationship', 0)

        if setup.relationship is None:
            setup.relationship = relationship + 1
            user['relationship'] = setup.relationship

        accounts[setup.chosen_account.id] = {
            'id': int(setup.chosen_account.id),
            'name': setup.chosen_account.attributes.name,
            'image': {
                'x': setup.chosen_balance.x,
                'y': setup.chosen_balance.y,
                'hash': setup.screenshot_hash.hash.tolist()
            },
            'relationship': setup.relationship
        }
        user['accounts'] = accounts
        _write_user_file(query.from_user.id, user)

        query.message.reply_text(i18n.t('setup.setup_complete'))
        logger.info(f'{query.from_user.name}:{query.from_user.id} confirmed the account setup, '
                    f'writing {query.from_user.id}.json')
    elif query.data == "0":
        query.message.reply_text(i18n.t('setup.setup_canceled'))
        logger.info(f'{query.from_user.name}:{query.from_user.id} canceled the account setup')

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    del context.user_data['setup']
    update.message.reply_text(i18n.t('setup.setup_canceled'))
    logger.info(f'{update.message.from_user.name}:{update.message.from_user.id} canceled the account setup')
    return ConversationHandler.END


def timeout(update: Update, context: CallbackContext) -> int:
    del context.user_data['setup']
    logger.info(f'{update.message.from_user.name}:{update.message.from_user.id} timed out account setup')
    return ConversationHandler.END
