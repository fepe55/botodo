import os
import json
import logging

from dotenv import load_dotenv

from telegram.ext import Updater, CommandHandler
from telegram.parsemode import ParseMode

load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

API_TOKEN = os.getenv('API_TOKEN')

TODO_FILE_PATH = 'todo-{}.json'
DONE_FILE_PATH = 'done-{}.json'


def _pop_todo(todo_list, todo_id):
    todo_index = None
    for index, todo in enumerate(todo_list):
        if str(todo['id']) == str(todo_id):
            todo_index = index

    if todo_index is not None:
        todo = todo_list.pop(todo_index)
        return {'success': True, 'todo_list': todo_list, 'todo': todo}
    return {'success': False, 'error_msg': 'Error en el id del todo'}


def _mark_as_done(args, chat_id):
    result = _get_id_from_args(args, chat_id)
    if not result['success']:
        return result
    todo_id = result['todo_id']
    todo_list = _get_todo_list(chat_id)
    result = _pop_todo(todo_list, todo_id)
    if not result['success']:
        return result
    todo = result['todo']
    todo_list = result['todo_list']
    _save_todo_list(todo_list, chat_id)
    done_list = _get_done_list(chat_id)
    done_list.append(todo)
    _save_done_list(done_list, chat_id)
    return {'success': True}


def _mark_as_undone(args, chat_id):
    result = _get_id_from_args(args, chat_id)
    if not result['success']:
        return result
    todo_id = result['todo_id']
    done_list = _get_done_list(chat_id)
    result = _pop_todo(done_list, todo_id)
    if not result['success']:
        return result
    todo = result['todo']
    done_list = result['todo_list']
    _save_done_list(done_list, chat_id)
    todo_list = _get_todo_list(chat_id)
    todo_list.append(todo)
    _save_todo_list(todo_list, chat_id)
    return {'success': True}


def _remove_todo(args, chat_id):
    result = _get_id_from_args(args, chat_id)
    if not result['success']:
        return result

    todo_id = result['todo_id']
    done_list = _get_done_list(chat_id)
    result = _pop_todo(done_list, todo_id)
    if not result['success']:
        todo_list = _get_todo_list(chat_id)
        result = _pop_todo(todo_list, todo_id)
        if not result['success']:
            return result

    _save_todo_list(todo_list, chat_id)
    return {'success': True}


def _add_todo(chat_id, todo_msg):
    todo_list = _get_todo_list(chat_id)
    if todo_list:
        max_id = max([todo['id'] for todo in todo_list])
        next_id = max_id + 1
    else:
        next_id = 1
    todo_list.append({'id': next_id, 'msg': todo_msg})
    _save_todo_list(todo_list, chat_id)


def _get_todo_list(chat_id):
    file_path = TODO_FILE_PATH.format(chat_id)
    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            todo_list = json.load(f)
    else:
        todo_list = []

    return todo_list


def _get_done_list(chat_id):
    file_path = DONE_FILE_PATH.format(chat_id)
    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            done_list = json.load(f)
    else:
        done_list = []

    return done_list


def _save_todo_list(todo_list, chat_id):
    file_path = TODO_FILE_PATH.format(chat_id)
    with open(file_path, 'w') as f:
        f.write(json.dumps(todo_list))


def _save_done_list(done_list, chat_id):
    file_path = DONE_FILE_PATH.format(chat_id)
    with open(file_path, 'w') as f:
        f.write(json.dumps(done_list))


def _print_list(update, todo_list):
    message = ''
    for todo in todo_list:
        message += '\[{}] `{}`\n'.format(todo['id'], todo['msg'])

    if not message:
        message = 'Empty'
    # Message as a reply
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def _get_id_from_args(args, chat_id):
    if not args:
        return {'success': False, 'error_msg': 'No pasaste argumentos'}
    if len(args) > 1:
        return {'success': False, 'error_msg': 'Pasaste más de un argumento'}
    todo_id = args[0]
    return {'success': True, 'todo_id': todo_id}


def cmd_todo(bot, update):
    todo_list = _get_todo_list(update.effective_chat.id)
    _print_list(update, todo_list)


def cmd_add(bot, update, args):
    if not args:
        cmd_help(bot, update)
        return
    todo_msg = ' '.join(args)
    _add_todo(update.effective_chat.id, todo_msg)
    cmd_todo(bot, update)
    # Message as a reply
    # update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    # Message as a standalone message
    # bot.send_message(
    #     update.message.chat_id, message, parse_mode=ParseMode.MARKDOWN
    # )


def cmd_done(bot, update, args):
    ''' If no args, list everything done. If args, must be the ID '''
    chat_id = update.effective_chat.id
    if not args:
        done_list = _get_done_list(chat_id)
        _print_list(update, done_list)
        return
    result = _mark_as_done(args, chat_id)
    if not result['success']:
        msg = result['error_msg']
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        cmd_help(bot, update)
    else:
        msg = 'Todo marked as done'
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def cmd_undo(bot, update, args):
    if not args:
        msg = 'Falta el ID'
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        help()
        return
    chat_id = update.effective_chat.id
    result = _mark_as_undone(args, chat_id)
    if not result['success']:
        msg = result['error_msg']
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        cmd_help(bot, update)
    else:
        msg = 'Todo marked as undone'
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def cmd_remove(bot, update, args):
    if not args:
        msg = 'Falta el ID'
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        help()
        return
    chat_id = update.effective_chat.id
    result = _remove_todo(args, chat_id)
    if not result['success']:
        msg = result['error_msg']
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        cmd_help(bot, update)
    else:
        msg = 'Todo removed'
        update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def cmd_help(bot, update):
    message = ''
    message += '/todo - Te muestra lo que hay para hacer\n'
    message += '/add <texto> - Agregás un todo\n'
    message += '/done <id> - Marcás como hecho\n'
    message += '/done - Ves todo lo hecho\n'
    message += '/undo <id> - Desmarcás como hecho\n'
    message += '/remove <id> - Eliminás completamente uno\n'
    message += '/help - Mostrar esta ayuda\n'
    bot.send_message(
        update.message.chat_id, message, parse_mode=ParseMode.MARKDOWN
    )


def main():

    updater = Updater(API_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('help', cmd_help))
    dp.add_handler(CommandHandler('todo', cmd_todo))
    dp.add_handler(CommandHandler('done', cmd_done, pass_args=True))
    dp.add_handler(CommandHandler('undo', cmd_undo, pass_args=True))
    dp.add_handler(CommandHandler('remove', cmd_remove, pass_args=True))
    dp.add_handler(CommandHandler('add', cmd_add, pass_args=True))
    # dp.add_handler(MessageHandler(Filters.command, cmd_help))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
