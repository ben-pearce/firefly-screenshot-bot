import logging
import os

import i18n
from telegram import Update
from telegram.ext import (CallbackContext, CommandHandler, Updater)

from firefly_bot.balance import conv_handler as balance_conv_handler
from firefly_bot.config import config
from firefly_bot.manage import conv_handler as manage_conv_handler
from firefly_bot.setup import conv_handler as setup_conv_handler
from firefly_bot.utils import _write_user_file

logger = logging.getLogger(__name__)


def start(update: Update, _: CallbackContext):
    if update.effective_user.id not in config.get('bot').get('users'):
        return

    user_file = os.path.join(config.get('bot').get('storage').get('path'), f'{update.message.from_user.id}.json')
    if not os.path.exists(user_file):
        _write_user_file(update.effective_user.id, dict())

        update.message.reply_markdown(i18n.t('general.welcome') + i18n.t('general.help'))
        logger.info(f'New user {update.message.from_user.name}:{update.message.from_user.id} created')


def info(update: Update, _: CallbackContext):
    if update.effective_user.id not in config.get('bot').get('users'):
        return

    update.message.reply_markdown(i18n.t('general.help'))
    logger.info(f'User {update.message.from_user.name}:{update.message.from_user.id} used help command')


def main() -> None:
    updater = Updater(config.get('telegram').get('token'))
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', info)

    # Ordering is important here!
    dispatcher.add_handler(manage_conv_handler)
    dispatcher.add_handler(setup_conv_handler)
    dispatcher.add_handler(balance_conv_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
