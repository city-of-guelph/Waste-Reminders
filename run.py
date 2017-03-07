import logging, logging.config

## Setup logging
logging.config.fileConfig('logging.conf')

from app import app
import reminders
import os

isProduction = os.environ.get('IS_PRODUCTION', None)
port = int(os.environ.get("PORT", 5000))

if (__name__ == "__main__"):   
    if isProduction:
        #reminders.startScheduler()
        app.run(host='0.0.0.0', debug=False, port=port)
    else:
        #reminders.startScheduler()
        app.run(host='0.0.0.0', debug=True, use_reloader=False)