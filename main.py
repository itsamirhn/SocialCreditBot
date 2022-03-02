import logging

import telegram
from telegram import Update, Chat
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, PicklePersistence

from settings import BOT_TOKEN, SUPER_ADMIN_ID, DEBUG, WEBHOOK_URL, BLACKLIST_ID, BACKUP_CHANNEL_ID, db

logger = logging.getLogger(__name__)


def save_update(f):
    def g(update: Update, context: CallbackContext):
        response = f(update, context)
        if not DEBUG:
            db.updates.insert_one(update.to_dict())
        return response
    return g


def forward_update(f):
    def g(update: Update, context: CallbackContext):
        response = f(update, context)
        if (Filters.video | Filters.photo | Filters.document)(update):
            update.message.forward(BACKUP_CHANNEL_ID)
        return response
    return g


@save_update
def start_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    message = update.message
    if message.chat.type == Chat.PRIVATE:
        message.reply_markdown_v2(
            fr'''Hi {user.mention_markdown_v2()} 🇨🇳\!
Add me to group first, then anybody in the chat can reply a message and credit the sender with "\+" and "\-" as many as they want\.
'''
        )
    else:
        message.reply_text('I have already run my system in here...')


@save_update
def credit_message(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    user = message.reply_to_message.from_user
    context.chat_data.setdefault('silence', False)
    silence_mode = context.chat_data['silence']
    if 'battle' in context.chat_data:
        context.chat_data.setdefault('battle', {})
        credit_dic = context.chat_data['battle']
        silence_mode = True
    else:
        credit_dic = context.chat_data
    if user.is_bot:
        if user.id == context.bot.id:
            text = "You thought you can credit the GOD?"
        else:
            text = "No matter what, this bot doesn't worth at all."
    else:
        value = +1 if context.match.group(1) == '+' else -1
        if len(context.match.group(3)) > 0:
            points = int(context.match.group(3))
        else:
            points = len(context.match.group(1) + context.match.group(2))
        if user.id in BLACKLIST_ID:
            value = -1
        elif message.from_user.id != SUPER_ADMIN_ID:
            points = min(points, 10)
        points = value * points
        credit_dic.setdefault(user.id, {'name': user.first_name, 'points': 0})
        if message.from_user.id != SUPER_ADMIN_ID and message.from_user.id == user.id:
            if points > 0:
                text = "Do You think you are smart? Idiot.\nYou can't credit to yourself."
            else:
                credit_dic[user.id]['points'] -= points
                text = "Ok Idiot, You lost it"
        else:
            credit_dic[user.id]['points'] += points
            text = 'Ok, {} {} {} {}!'.format(
                user.first_name,
                'got' if points > 0 else 'lost',
                abs(points),
                'points' if abs(points) > 1 else 'point'
            )
    if not silence_mode:
        message.reply_text(text)


def my_credits_command(update: Update, context: CallbackContext) -> None:
    if 'battle' in context.chat_data:
        return
    message = update.effective_message
    user = update.effective_user
    context.chat_data.setdefault(user.id, {'name': user.first_name, 'points': 0})
    points = context.chat_data[user.id]['points']
    message.reply_text(f'You worth {points} points.' if points != 0 else 'You worth nothing.')


def credits_command(update: Update, context: CallbackContext) -> None:
    if 'battle' in context.chat_data:
        return
    message = update.effective_message
    if not message.reply_to_message:
        message.reply_text("You should reply this command to someone to see their credits.")
        return
    user = message.reply_to_message.from_user
    if user.id == context.bot.id:
        message.reply_text("How dare you?")
        return
    context.chat_data.setdefault(user.id, {'name': user.first_name, 'points': 0})
    points = context.chat_data[user.id]['points']
    message.reply_text(
        f'{user.first_name} worth {points} points.' if points != 0 else f'{user.first_name} worth nothing.')


def rank_command(update: Update, context: CallbackContext) -> None:
    if 'battle' in context.chat_data:
        return
    message = update.effective_message
    leaderboard = []
    for key, value in context.chat_data.items():
        if type(key) is int:
            leaderboard.append((value['points'], value['name']))
    leaderboard.sort(reverse=True)
    if len(leaderboard) < 4:
        message.reply_text('Not enough people has got credited yet!')
        return
    best = leaderboard[:3]
    worst = sorted(leaderboard[-3:])
    text = ''

    text += 'Best credits:\n'
    if len(best) == 0:
        text += 'No one yet!'
    for row in best:
        text += '{} ➔ {} {}\n'.format(
            row[1],
            str(row[0]),
            'points' if abs(row[0]) > 1 else 'point'
        )

    text += '\nWorst credits:\n'
    if len(worst) == 0:
        text += 'No one yet!'
    for row in worst:
        text += '{} ➔ {} {}\n'.format(
            row[1],
            str(row[0]),
            'points' if abs(row[0]) > 1 else 'point'
        )
    message.reply_text(text)


def private_message(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Du-uh, The Social Credit System only works in groups.')


def reset_command(update: Update, context: CallbackContext) -> None:
    context.chat_data.clear()
    update.message.reply_text('OK!')


def silence_command(update: Update, context: CallbackContext) -> None:
    if 'battle' in context.chat_data:
        return
    context.chat_data.setdefault('silence', False)
    context.chat_data['silence'] = not context.chat_data['silence']
    update.message.reply_text('Silence mode turned {}!'.format('ON' if context.chat_data['silence'] else 'OFF'))


def battle_command(update: Update, context: CallbackContext) -> None:
    if 'battle' in context.chat_data:
        leaderboard = []
        for key, value in context.chat_data['battle'].items():
            if type(key) is int:
                leaderboard.append((value['points'], value['name']))
        leaderboard.sort(reverse=True)
        if len(leaderboard) > 0:
            text = 'Battle Finished.\n\nLeaderboard:\n'
            for row in leaderboard:
                text += '{} ➔ {} {}\n'.format(
                    row[1],
                    str(row[0]),
                    'points' if abs(row[0]) > 1 else 'point'
                )
        else:
            text = 'Bruh, Are you kidding me? Battle mode finished.'
        del context.chat_data['battle']
        update.message.reply_text(text)
    else:
        context.chat_data['battle'] = {}
        update.message.reply_text(
            'Battle mode started!\n\nAll credits reset temporary. None of the commands will work till the end of the '
            'battle.')


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


@save_update
@forward_update
def any_message(update, context):
    pass


def main() -> None:
    persistence = PicklePersistence(filename='SocialCreditBot')

    updater = Updater(BOT_TOKEN, persistence=persistence)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start_command))
    dispatcher.add_handler(CommandHandler('mycredits', my_credits_command, filters=Filters.chat_type.groups))
    dispatcher.add_handler(CommandHandler('credits', credits_command, filters=Filters.chat_type.groups))
    dispatcher.add_handler(CommandHandler('rank', rank_command, filters=Filters.chat_type.groups))
    dispatcher.add_handler(CommandHandler('reset', reset_command,
                                          filters=Filters.chat_type.groups & Filters.user(user_id=SUPER_ADMIN_ID)))
    dispatcher.add_handler(CommandHandler('silence', silence_command,
                                          filters=Filters.chat_type.groups & Filters.user(user_id=SUPER_ADMIN_ID)))
    dispatcher.add_handler(CommandHandler('battle', battle_command, filters=Filters.chat_type.groups))

    dispatcher.add_handler(MessageHandler(
        ~Filters.user(user_id=BLACKLIST_ID) &
        Filters.text & ~Filters.command & Filters.reply & Filters.regex(
            r'^([+-])(\1*)(\d*)') & Filters.chat_type.groups,
        credit_message
    ))
    dispatcher.add_handler(MessageHandler(Filters.chat_type.private, private_message))

    dispatcher.add_handler(MessageHandler(Filters.all, any_message))
    dispatcher.add_error_handler(error)

    if DEBUG:
        logger.info(f"Start Polling...")
        updater.start_polling()
    else:
        logger.info(f"Webhook on port: 5000")
        updater.start_webhook(listen="0.0.0.0", port=5000, url_path=BOT_TOKEN, webhook_url=WEBHOOK_URL + BOT_TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
