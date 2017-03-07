import os
from datetime import timedelta
basedir = os.path.abspath(os.path.dirname(__file__))
isProduction = os.environ.get('IS_PRODUCTION', None)

SECRET_KEY = "SECRET"

PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

""" Google Analytics Keys """
ANALYTICS_KEY_PRIMARY = "<UPDATE>"
ANALYTICS_KEY_SECONDARY = "<UPDATE>"

""" Slack Webhook URL """
SLACK_WEBHOOK_URL = "<UPDATE>"
SLACK_CHANNEL = "<UPDATE>"
SLACK_USERNAME = "<UPDATE>"

""" Set Database URL from Environment variable """
if os.environ.get('DATABASE_URL') is None:
    DATABASE_FILE = "waste.db"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" +  os.path.join(basedir, DATABASE_FILE)
    TEMPLATES_AUTO_RELOAD = True    
else:
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

SQLALCHEMY_TRACK_MODIFICATIONS = False

""" Set some config values specifically for Production """
if isProduction:

    """ Assuming in Production we will always be running on HTTPS """
    SESSION_COOKIE_SECURE = True
        
    SQLALCHEMY_ECHO=False
    
    """ Twilio configuration """
    TWILIO_ACCOUNT_SID = "<UPDATE>"
    TWILIO_AUTH_TOKEN  = "<UPDATE>"
    TWILIO_FROM_NUMBER = "<UPDATE>"
    
    """ EMAIL Configuration """
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_SERVER = "<UPDATE>"
    MAIL_FROM = "<UPDATE>"
    MAIL_ERROR_TO = "<UPDATE>"
else:
    
    """ Twilio configuration """
    TWILIO_ACCOUNT_SID = "<UPDATE>"
    TWILIO_AUTH_TOKEN = "<UPDATE>"
    TWILIO_FROM_NUMBER = "<UPDATE>"  #Valid test phone number

    """ EMAIL Configuration """
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_SERVER = "<UPDATE>"
    MAIL_FROM = "<UPDATE>"
    MAIL_ERROR_TO = "<UPDATE>"

EMAIL_LOGO = os.path.join("app","static","img", "cog_logo.png")
EMAIL_WASTE_LOGO = os.path.join("app","static","img", "GiveWaste_logo_small.png")

DATA_FOLDER = os.path.join("app", "data")
DATA_CONFIG = os.path.join(DATA_FOLDER, 'config.ini')
DATA_STAT_HOLIDAYS = os.path.join(DATA_FOLDER, 'StatHolidays.txt')
DATA_IDINFO = os.path.join(DATA_FOLDER, 'IDInfo.txt')
DATA_WEEK_A_SCHEDULE = os.path.join(DATA_FOLDER, 'WeekASchedule.txt')
DATA_WEEK_B_SCHEDULE = os.path.join(DATA_FOLDER, 'WeekBSchedule.txt')
DATA_WEEK_Z_SCHEDULE = os.path.join(DATA_FOLDER, 'WeekZSchedule.txt')
DATA_ADDRESS_LIST = os.path.join(DATA_FOLDER, 'addressList.txt')
DATA_SPECIAL_EVENTS = os.path.join(DATA_FOLDER, 'SpecialEvents.txt')

""" Google Recaptcha details """
RECAPTCHA_SITE_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_SECRET_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"
if os.environ.get('DISABLE_RECAPTCHA') is None:
    RECAPTCHA_ENABLED = True
else:
    RECAPTCHA_ENABLED = False

""" Flask-Security config """
SECURITY_USER_IDENTITY_ATTRIBUTES = "user_name"
SECURITY_URL_PREFIX = "/admin"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = "<UPDATE>"

""" Flask-Security URLs, overridden because they don't put a / at the end """
SECURITY_LOGIN_URL = "/login/"
SECURITY_LOGOUT_URL = "/logout/"

SECURITY_POST_LOGIN_VIEW = "/admin/"
SECURITY_POST_LOGOUT_VIEW = "/admin/"
SECURITY_POST_REGISTER_VIEW = "/admin/"

""" Flask-Security features """
SECURITY_REGISTERABLE = False
SECURITY_SEND_REGISTER_EMAIL = False