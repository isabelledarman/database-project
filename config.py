import os
from dotenv import load_dotenv

load_dotenv()   # reads .env into the environment

DB_USER = 'root'
DB_NAME = 'project3510'
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = 'localhost'

# Flask app settings (only used by the web app, view.py)
APP_HOST = '127.0.0.1'
APP_PORT = 5001
APP_DEBUG = True