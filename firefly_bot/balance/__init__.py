from telegram.ext import CallbackQueryHandler, ConversationHandler, Filters, MessageHandler

from firefly_bot.balance import commands

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(Filters.photo, commands.update_balance_from_image)],
    states={
        commands.ACCOUNT: [CallbackQueryHandler(commands.choose_account_to_update)],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text, commands.timeout)]
    },
    fallbacks=[],
    conversation_timeout=120
)
