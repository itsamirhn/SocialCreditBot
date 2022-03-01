import logging
import os

DEBUG = os.environ.get('DEBUG', 'False').lower() != 'False'.lower()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.environ.get('TOKEN')

SUPER_ADMIN_ID = int(os.environ.get('SUPER_ADMIN_ID', 0))

WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

try:
    BLACKLIST_ID = [int(i) for i in os.environ.get("BLACKLIST_ID").split(' ')]
except:
    BLACKLIST_ID = []
