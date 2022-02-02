import logging
import os

DEBUG = True

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = 'TOKEN'

SUPER_ADMIN_ID = 0

PORT = int(os.environ.get('PORT', 8443))

WEBHOOK_URL = 'https://yourherokuappname.herokuapp.com/' + BOT_TOKEN
