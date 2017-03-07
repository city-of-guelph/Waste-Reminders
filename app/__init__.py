import logging
   
logger = logging.getLogger("waste.web")
logger.addHandler(logging.NullHandler())
logger.info("starting waste application")
#logger.handlers.extend(logging.getLogger("gunicorn.error").handlers)


from flask import Flask, render_template, redirect, request, \
    url_for, flash, make_response, abort, session
from flask_admin import BaseView, expose
import flask_admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib import sqla
from flask_admin import helpers as admin_helpers
from flask_bower import Bower
from functools import wraps
from flask_recaptcha import ReCaptcha
from flask_security import Security, SQLAlchemyUserDatastore, \
    login_required, current_user
from flask_security.forms import LoginForm
from flask_security.utils import encrypt_password, verify_and_update_password
from flask_login import user_logged_in, user_logged_out
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField
from wtforms.validators import InputRequired
from slack_log_handler import SlackLogHandler

import os
from datetime import date, datetime, timedelta
from urllib import quote, unquote
import sys
import traceback
import random

from validationModule import validateForm, validateOpts, militaryToStandard, removeDuplicates
from parsingModule import getSchedule, getIDInfo, generateHomepageDropdown
from settingsModule import getSetting
import config

app = Flask(__name__)
app.config.from_object('config')

Bower(app)
recaptcha = ReCaptcha(app=app)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

db = SQLAlchemy(app)
from dbModule import Logs, ScheduledAlerts, Subscription, User, Role, MessageLog, writeMessageLog


"""
Create logging handler

    Send logs with level ERROR and higher to Slack when running in Production
    
    Write all other logs to local file 
"""
if config.isProduction:
    slack_handler = SlackLogHandler(config.SLACK_WEBHOOK_URL, channel=config.SLACK_CHANNEL, username=config.SLACK_USERNAME)
    slack_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    slack_handler.setLevel(logging.ERROR)
    app.logger.addHandler(slack_handler) # register flask application to slack
    logger.addHandler(slack_handler) # register application logger to slack

class ExtendedLoginForm(LoginForm):
    """Extend the Flask-Security login form to use Username as the login field
       instead of the default email field

    """
    email = StringField('Username', [InputRequired()])

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore, login_form=ExtendedLoginForm)


class MyUserModelView(sqla.ModelView):
    """Create User Model view for admin panel """
    
    column_list = ['first_name', 'last_name', 'user_name', 'active', 'confirmed_at']
            
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))

    # Log user deletions
    def after_model_delete(self, model):
        write_log(current_user.user_name, "Deleted user: %s" % model.user_name)

    # Log user updates
    def after_model_change(self, form, model, is_created):
        if is_created:
            msg = "Added new user: %s"
        else:
            msg = "Updated existing user: %s"
        write_log(current_user.user_name, msg % model.user_name)

    #Ensure password is encrypted when new user is created/updated       
    def on_model_change(self, form, model, is_created):
        verify_and_update_password(model.password, model)        
        

class MyModelView(ModelView):
    """
    Create Subscription Model view for admin panel
    """
    
    column_default_sort = ("created", True)
    column_searchable_list = ('address','email','call_phone_number', 'text_phone_number')
    can_export = True
    form_excluded_columns = ['created']
    form_optional_types = (db.String)
    form_choices = {
                   'schedule': [ ('Week A', 'Week A'), ('Week B', 'Week B'),('Week Z', 'Week Z'), ('Please contact the city.', 'No Week (ZZ)')],
                   'notification_time': [('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), 
                                         ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15'), ('16', '16'), 
                                         ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), ('21', '21'), ('22', '22'), ('23', '23')] 
                   }
    
    def __init__(self, dbName, dbSession, **kwargs):
        # You can pass name and other parameters if you want to
        super(MyModelView, self).__init__(dbName, dbSession, **kwargs)
        
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False
  
    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))

 
class MyLogsView(ModelView):
    """
    Create Logs Model view for admin panel
    """
    can_export = True
    can_create = False
    can_edit = False
    can_delete = False
    column_default_sort = ("datetime", True)
    column_searchable_list = ('user','datetime')
    form_optional_types = (db.String)
    
    def __init__(self, dbName, dbSession, **kwargs):
        # You can pass name and other parameters if you want to
        super(MyLogsView, self).__init__(dbName, dbSession, **kwargs)
      
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False
    
    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class MyMessageLogsView(ModelView):
    """
    Create Message Logs Model view for admin panel
    """

    can_export = True
    can_create = False
    can_edit = False
    can_delete = False
    column_default_sort = ("datetime", True)
    column_searchable_list = ('collection_weeks', 'collection_days', 'message_type', 'sent', 'datetime', 'method')
    form_optional_types = (db.String)
    
    def __init__(self, dbName, dbSession, **kwargs):
        # You can pass name and other parameters if you want to
        super(MyMessageLogsView, self).__init__(dbName, dbSession, **kwargs)
      
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False
    
    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class MyScheduledAlertsView(ModelView):
    """
    Create Scheduled Alerts Model view for admin panel
    """

    column_searchable_list = ('user','datetime')
    can_export = True
    can_create = False
    can_edit = False
    column_default_sort = ("datetime", True)
    form_optional_types = (db.String)
    
    def __init__(self, dbName, dbSession, **kwargs):
        # You can pass name and other parameters if you want to
        super(MyScheduledAlertsView, self).__init__(dbName, dbSession, **kwargs)
        
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False
  
    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))
        
    # Log alert deletions
    def after_model_delete(self, model):
        write_log(current_user.user_name, "Deleted scheduled alert: %s" % model.message)


class MyAdminView(FileAdmin):
    """
    Create Data File folder view for admin panel
    """

    editable_extensions = ('txt','ini')
    can_delete = False
    can_rename = False
    can_upload = False
    can_mkdir = False
    can_delete_dirs = False
    
    def __init__(self, path, folder, **kwargs):
        super(MyAdminView, self).__init__(path, folder, **kwargs)
        
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False
    
    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))
        
    def on_edit_file(self,full_path,path):
        """
        Open file for read when edit file is clicked
        """

        lines = None
        with open(full_path) as f:
            lines = f.readlines()
            f.close()
        with open(full_path, 'w') as g:
            i = 0
            for l in lines:
                if l.strip():
                    if i != 0:
                        g.write('\n')
                    g.write(l.strip())
                    i += 1
            g.close()
    

class MyAlertsView(BaseView):
    """
    Create Alerts tab view for admin panel
    """
    @expose('/')
    
    def index(self):
        return self.render('admin/alerts.html')
    
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin'):
            return True

        return False
    
    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))

# Create admin
admin = flask_admin.Admin(
    app,
    'Guelph Waste',
    base_template='admin/adminMaster.html',
    template_mode='bootstrap3',
)

admin.add_view(MyModelView(Subscription, db.session, name="Subscriptions", endpoint='database'))
path = os.path.join(os.path.dirname(__file__), 'data')
admin.add_view(MyAdminView(path, '/data/', name="File Manager", endpoint='files'))
admin.add_view(MyAlertsView(name='Send Alerts', endpoint='alerts'))
admin.add_view(MyScheduledAlertsView(ScheduledAlerts, db.session, name="Scheduled Alerts", endpoint='Scheduled Alerts'))#
#admin.add_view(MyUserModelView(Role, db.session, name="Roles")) # Hide Role tab until it is needed
admin.add_view(MyUserModelView(User, db.session, name="Users"))
admin.add_view(MyLogsView(Logs, db.session, name="Logs", endpoint='logs'))
admin.add_view(MyMessageLogsView(MessageLog, db.session, name="Message Logs", endpoint='message_log'))


@security.context_processor
def security_context_processor():
    """
    Define a context processor for merging flask-admin's 
    template context into the flask-security views.

    """
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )


"""
    GENERAL NOTES
    isoweekday() sets Monday to 1 and Sunday to 7
    City of Guelph data has Sunday as 1 and Saturday as 7
                City    isoweekday()
    Sunday       1          7
    Monday       2          1
    Tuesday      3          2
    Wednesday    4          3
    Thursday     5          4
    Friday       6          5
    Saturday     7          6
    
    To go from isoweekday() -> City format:
    (isoweekday() % 7) + 1

"""

#### GLOBAL VARS ######
addressDictionary = generateHomepageDropdown() # list of all addresses
########################


def getPickupDates():
    """
    Generate list of pickup dates within given range of weeks  

    """

    pickupDates = []
    with open(config.DATA_STAT_HOLIDAYS) as f:
        statDates = f.readlines()
    collectionDayNum = session.get('collectionDayNum', None)
    
    processWeek = 1      
    for x in range(1,106):
        holidayThisWeek, pickupDate = statThisWeek(collectionDayNum, processWeek, statDates) #for all 52 weeks, run this function, to generate the pickup dates for the year
        if pickupDate:
            for p in pickupDate:
                pickupDates.append(p)
        processWeek += 1
    return pickupDates


def statThisWeek(collectionDayNum, thisWeekNum, statDates):
    """
    Generate list of pickup dates and determine if there is a stat holiday
    for the given week

    """

    pickupDate = []
    dateToAppend = None
    statDate = None
    holidayThisWeek = False

    todayNum = (date.today().isoweekday() % 7) + 1 #todays weekday number, by city standards
    dateToUse = date.today() + timedelta(weeks=thisWeekNum - int(date.today().strftime("%U")) - (todayNum == 1)) #get a date in the week that we are processing
    checkDate = datetime.strptime(str(dateToUse), '%Y-%m-%d').date()
    checkWeek = checkDate.strftime("%U")
    checkYear = checkDate.year
    if checkWeek == "53":
        checkWeek = "52"
    elif checkWeek == "00":
        checkWeek = "52"
        checkYear = checkYear - 1
    
    for line in statDates:
        statDate = datetime.strptime(line.strip() , '%d/%m/%Y').date() # convert the dd/mm/yyyy to an actual Date
        statWeek = statDate.strftime("%U") # which week the date falls on
        statYear = statDate.year

        if statWeek == "00":
            statWeek = "52"
            statYear = statYear - 1
            
        if statYear == checkYear and statWeek == checkWeek: # if the week we're processing contains the stat holiday
            holidayThisWeek = True # we have a holiday
            break
    dateToUse = date.today() + timedelta(weeks=thisWeekNum - int(date.today().strftime("%U")) - (todayNum == 1)) #get a date in the week that we are processing

    if collectionDayNum[0] != '': # so long as we don't have a blank list of pickup days (Week ZZ)
        for i in collectionDayNum:
            dateToAppend = (dateToUse+timedelta(days=int(i)-todayNum)) #generate the list of collection dates

            if dateToAppend >= statDate:# and dateToAppend.isocalendar()[1] == statWeek:
                dateToAppend += timedelta(days=1) #account for stat holidays by pushing everything on or after to a stat holiday one forward

            pickupDate.append(dateToAppend.isoformat())

    return holidayThisWeek, pickupDate


@user_logged_in.connect_via(app)
def on_user_logged_in(sender, user):
    write_log(user.user_name, "User logged in")
    
    
@user_logged_out.connect_via(app)
def on_user_logged_out(sender, user):
    write_log(user.user_name, "User logged out")


def write_log(user, note):
    myLogs = Logs()
    myLogs.writeLog(user, note)
    

from contactModule import TwilioContact, EmailContact
myTwilioContact = TwilioContact(db, writeMessageLog, logger)
myEmailContact = EmailContact(db, writeMessageLog, logger)
from app import views
