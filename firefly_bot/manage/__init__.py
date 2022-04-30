from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler

from firefly_bot.manage import commands

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('manage', commands.menu)],
    states={
        commands.MENU: [CallbackQueryHandler(commands.menu_choice)],
        commands.DELETE: [CallbackQueryHandler(commands.delete_confirm)],
        commands.DELETE_RELATIONSHIP: [CallbackQueryHandler(commands.delete_relationship_confirm)]
    },
    fallbacks=[]
)
