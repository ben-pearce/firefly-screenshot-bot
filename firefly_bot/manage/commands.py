import copy
import json
import logging
from collections import defaultdict
from typing import Callable

import i18n
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from firefly_bot.utils import _get_user_file, _write_user_file

MENU, RESET, UPDATE, DELETE, DELETE_RELATIONSHIP, LIST, RAW = range(7)


logger = logging.getLogger(__name__)


def _check_has_accounts(func: Callable):
    def wrapper(update: Update, context: CallbackContext):
        user = _get_user_file(update.effective_user.id)
        if 'accounts' in user and len(user.get('accounts')) > 0:
            return func(update, context)
        else:
            update.effective_message.reply_text(i18n.t('manage.no_accounts'))
            return ConversationHandler.END
    return wrapper


@_check_has_accounts
def _list_accounts(update: Update, _: CallbackContext) -> int:
    user = _get_user_file(update.effective_user.id)
    accounts_by_relationship = defaultdict(list)
    for acc in user.get('accounts').values():
        accounts_by_relationship[acc.get('relationship')].append(acc)

    update.effective_message.reply_markdown('\n'.join(f'`Group {r}`: ' + ', '
                                                      .join(f'`{acc.get("id")}`:{acc.get("name")}' for acc in g)
                                                      for r, g in accounts_by_relationship.items()))
    return ConversationHandler.END


def _show_raw_user(update: Update, _: CallbackContext) -> int:
    user = _get_user_file(update.effective_user.id)
    update.effective_message.reply_markdown(f"```{json.dumps(user, indent=2)}```")
    return ConversationHandler.END


@_check_has_accounts
def _delete(update: Update, _: CallbackContext) -> int:
    user = _get_user_file(update.effective_user.id)
    keyboard = []

    for account in user.get('accounts').values():
        keyboard.append([InlineKeyboardButton(
            text=account.get('name'),
            callback_data=account.get('id')
        )])
    keyboard.append([InlineKeyboardButton(text=i18n.t('general.cancel'), callback_data='no')])

    update.effective_message.reply_text(i18n.t('manage.choose_delete'),
                                        reply_markup=InlineKeyboardMarkup(keyboard))
    return DELETE


def delete_confirm(update: Update, context: CallbackContext) -> int:
    user = _get_user_file(update.effective_user.id)
    query = update.callback_query
    query.answer()

    if query.data == "no":
        update.effective_message.reply_text(i18n.t('general.operation_canceled'))

        logger.info(f'User {update.effective_user.name}:{update.effective_user.id} canceled '
                    f'deleting account')
        return ConversationHandler.END
    else:
        del_account = user.get('accounts').get(query.data)
        del user.get('accounts')[query.data]
        _write_user_file(update.effective_user.id, user)

        update.effective_message.reply_text(i18n.t('manage.account_deleted',
                                                   id=del_account.get('id'),
                                                   name=del_account.get('name')))
        logger.info(f'User {update.effective_user.name}:{update.effective_user.id} deleted account'
                    f' {del_account.get("id")}:{del_account.get("name")}')
        return ConversationHandler.END


@_check_has_accounts
def _delete_relationship(update: Update, context: CallbackContext) -> int:
    user = _get_user_file(update.effective_user.id)
    accounts_by_relationship = defaultdict(list)
    for acc in user.get('accounts').values():
        accounts_by_relationship[acc.get('relationship')].append(acc)

    keyboard = [[
        InlineKeyboardButton(text=', '.join(acc.get('name') for acc in g), callback_data=r)
    ] for r, g in accounts_by_relationship.items()]
    keyboard.append([InlineKeyboardButton(text=i18n.t('general.cancel'), callback_data='no')])
    update.effective_message.reply_markdown(
        i18n.t('manage.choose_relationship_delete'),
        reply_markup=InlineKeyboardMarkup(keyboard))
    return DELETE_RELATIONSHIP


def delete_relationship_confirm(update: Update, _: CallbackContext) -> int:
    user = _get_user_file(update.effective_user.id)
    query = update.callback_query
    query.answer()

    if query.data == "no":
        update.effective_message.reply_text(i18n.t('general.operation_canceled'))

        logger.info(f'User {update.effective_user.name}:{update.effective_user.id} canceled '
                    f'deleting relationship group')
        return ConversationHandler.END
    else:
        c = 0
        for account in copy.deepcopy(user.get('accounts')).values():
            if account.get('relationship') == int(query.data):
                del user.get('accounts')[account.get('id')]
                c += 1

        _write_user_file(update.effective_user.id, user)

        update.effective_message.reply_text(i18n.t('manage.relationship_accounts_deleted',
                                                   count=c,
                                                   group=query.data))
        logger.info(f'User {update.effective_user.name}:{update.effective_user.id} deleted {c} accounts '
                    f'which were part of group {query.data}')
        return ConversationHandler.END


@_check_has_accounts
def _reset(update: Update, _: CallbackContext) -> int:
    _write_user_file(update.effective_user.id, dict())
    update.effective_message.reply_text(i18n.t('manage.account_reset'))
    return ConversationHandler.END


def _update(update: Update, _: CallbackContext) -> int:
    return ConversationHandler.END


def menu_choice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    logger.info(f'User {update.effective_user.name}:{update.effective_user.id} chose menu option {query.data}')

    if query.data == str(LIST):
        return _list_accounts(update, context)
    elif query.data == str(RAW):
        return _show_raw_user(update, context)
    elif query.data == str(DELETE):
        return _delete(update, context)
    elif query.data == str(DELETE_RELATIONSHIP):
        return _delete_relationship(update, context)
    elif query.data == str(RESET):
        return _reset(update, context)
    elif query.data == str(UPDATE):
        return _update(update, context)


def menu(update: Update, _: CallbackContext) -> int:
    keyboard = [[
        InlineKeyboardButton(
            text="Reset",
            callback_data=RESET
        ),
        # InlineKeyboardButton(
        #     text="Update",
        #     callback_data=UPDATE
        # )
    ], [
        InlineKeyboardButton(
            text="Delete Account",
            callback_data=DELETE
        ),
        InlineKeyboardButton(
            text="Delete Relationship",
            callback_data=DELETE_RELATIONSHIP
        )
    ], [
        InlineKeyboardButton(
            text="List",
            callback_data=LIST
        ),
        InlineKeyboardButton(
            text="Raw",
            callback_data=RAW
        )
    ]]

    logger.info(f'User {update.message.from_user.name}:{update.message.from_user.id} opened menu')

    update.message.reply_markdown(i18n.t('general.menu'), reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU
