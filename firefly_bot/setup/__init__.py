from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, Filters, MessageHandler

from firefly_bot.setup import commands

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('setup', commands.account)],
    states={
        commands.ACCOUNT: [CallbackQueryHandler(commands.account_chosen)],
        commands.EXAMPLE: [MessageHandler(Filters.photo, commands.example)],
        commands.BALANCE: [CallbackQueryHandler(commands.balance_chosen)],
        commands.RELATED: [CallbackQueryHandler(commands.relation_chosen)],
        commands.CONFIRM: [CallbackQueryHandler(commands.confirm)],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text, commands.timeout)]
    },
    fallbacks=[CommandHandler('cancel', commands.cancel)],
    conversation_timeout=120
)
