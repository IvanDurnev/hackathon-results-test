from flask import request
from app import bot, dispatcher
from app.telegram_bot import bp, texts
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler, PollAnswerHandler, CallbackContext
from threading import Thread
from app.telegram_bot import handlers


dispatcher.add_handler(CommandHandler('start', handlers.command_start))
dispatcher.add_handler(CommandHandler('users_count', handlers.command_users_count))
dispatcher.add_handler(CommandHandler('tasks', handlers.user_tasks))
dispatcher.add_handler(MessageHandler(Filters.reply, callback=handlers.reply_message))
dispatcher.add_handler(MessageHandler(Filters.text, callback=handlers.text_message))
dispatcher.add_handler(MessageHandler(Filters.photo, callback=handlers.photo_message))
dispatcher.add_handler(MessageHandler(Filters.contact, callback=handlers.contact_message))
dispatcher.add_handler(MessageHandler(Filters.voice, callback=handlers.audio_message))
dispatcher.add_handler(CallbackQueryHandler(pattern='deleteMessage', callback=handlers.delete_message))


@bp.route('/telegram', methods=['GET', 'POST'])
def telegram():
    update = Update.de_json(request.get_json(force=True), bot=bot)
    thread = Thread(target=dispatcher.process_update, args=[update,], name='dispatcher')
    thread.start()
    return 'ok'

