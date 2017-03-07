import logging, logging.config

## Setup logging
logging.config.fileConfig('logging.conf')
logger = logging.getLogger("waste.reminder")
logger.addHandler(logging.NullHandler())
logger.info("Starting waste reminder application, job")

import os
import traceback
from datetime import datetime, date, timedelta
from slack_log_handler import SlackLogHandler

#Setup Background scheduler    
from apscheduler.schedulers.blocking import BlockingScheduler

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import and_, or_

from app.contactModule import TwilioContact, EmailContact
from app.parsingModule import generateSeasonalEvents, getSchedule
from app.validationModule import removeDuplicates
from app.settingsModule import getSetting
import config

#Initialize SQLAlchemy engine
Base = declarative_base()
engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
db = sessionmaker(bind=engine)

#Send errors to Slack if we are not running in debug
if config.isProduction:
    slack_handler = SlackLogHandler(config.SLACK_WEBHOOK_URL, channel=config.SLACK_CHANNEL, username=config.SLACK_USERNAME)
    slack_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    slack_handler.setLevel(logging.ERROR)
    logger.addHandler(slack_handler)

def getCurrentDateTime():
    return datetime.now()

class Logs(Base):
    __tablename__= "logs"
    id = Column(Integer, primary_key=True)
    user = Column(String(50), nullable=False)
    datetime = Column(DateTime, nullable=False)
    notes = Column(String(1000), nullable=False)
    
    def __init__(self, user="", datetime="", notes=""):
        self.user = user
        self.datetime = datetime
        self.notes = notes

    def __repr__(self):
        return '%r %r %r' % (self.user, self.datetime, self.notes)


class ScheduledAlerts(Base):
    __tablename__= "alerts"
    id = Column(Integer, primary_key=True)
    user = Column(String(50), nullable=False)
    options = Column(String(10),nullable=False)
    collection_weeks = Column(String(50), nullable=False)
    collection_days = Column(String(20), nullable=False)
    datetime = Column(DateTime, nullable=False)
    type = Column(String(10), nullable=False)
    sent = Column(Boolean)
    message = Column(String(1000), nullable=False)
    
    def __init__(self, user="", options="", collection_weeks="", collection_days="", datetime="", type="", sent=False, message=""):
        self.user = user
        self.options = options
        self.collection_weeks = collection_weeks
        self.collection_days = collection_days
        self.datetime = datetime
        self.type = type
        self.sent = sent
        self.message = message

    def __repr__(self):
        return '%r %r %r %r %r %r %r %r' % (self.user, self.options, self.collection_weeks, self.collection_days, self.datetime, self.type, self.sent, self.message)

    
class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    address = Column(String(255), nullable=False)
    address_id = Column(String(10), nullable=False)
    email = Column(String(255),nullable=True)
    email_active = Column(Boolean)
    opt_in = Column(String(10),nullable=False)
    call_phone_number = Column(String(10), nullable=True)
    call_number_active = Column(Boolean)
    text_phone_number = Column(String(10), nullable=True)
    text_number_active = Column(Boolean)
    collection_days = Column(String(20), nullable=False)
    schedule = Column(String(50), nullable=False)
    notification_time = Column(Integer,nullable=False)
    created = Column(DateTime, nullable=False)
    email_verification_code = Column(String(10),nullable=True)
    text_verification_code = Column(String(10),nullable=True)
    call_verification_code = Column(String(10),nullable=True)

    def __init__(self, address="", addressId="", email="", emailActive=False, optin="", callPhoneNumber="", callNumberActive=False, textPhoneNumber="", textNumberActive=False, collectiondays="", schedule="", notificationTime=19, created="", emailVerificationCode="", textVerificationCode="", callVerificationCode=""):
        self.address = address
        self.address_id = addressId
        self.email = email
        self.email_active = emailActive
        self.opt_in = optin
        self.call_phone_number = callPhoneNumber
        self.call_number_active = callNumberActive
        self.text_phone_number = textPhoneNumber
        self.text_number_active = textNumberActive
        self.collection_days = collectiondays
        self.schedule = schedule
        self.notification_time = notificationTime
        self.created = getCurrentDateTime()
        self.email_verification_code = emailVerificationCode
        self.text_verification_code = textVerificationCode
        self.call_verification_code = callVerificationCode

    def __repr__(self):
        return '%r %r %r %r %r %r %r %r %r %r %r %r %r %r %r %r' % (self.address, self.address_id, self.email, self.email_active, self.opt_in, self.call_phone_number, self.call_number_active, 
                                                                self.text_phone_number, self.text_number_active, self.collection_days, self.schedule, self.notification_time, self.created, 
                                                                self.email_verification_code, self.text_verification_code, self.call_verification_code)
       
       
class MessageLog(Base):
    __tablename__= "message_log"
    id = Column(Integer, primary_key=True)
    message_type = Column(String(20), nullable=False)
    method = Column(String(10), nullable=False)
    email = Column(String(255))
    phone_number = Column(String(10))
    options = Column(String(10))
    collection_weeks = Column(String(50))
    collection_days = Column(String(20))
    datetime = Column(DateTime, nullable=False)
    sent = Column(Boolean)
    notes = Column(String(1000))
    
    def __init__(self, message_type="", email="", phone_number="", options="", collection_weeks="", collection_days="", datetime="", method="", sent=False, notes=""):
        self.message_type = message_type
        self.email = email
        self.phone_number = phone_number
        self.options = options
        self.collection_weeks = collection_weeks
        self.collection_days = collection_days
        self.datetime = getCurrentDateTime()
        self.method = method
        self.sent = sent
        self.notes = notes

    def __repr__(self):
        return '%r %r %r %r %r %r %r %r %r %r' % (self.message_type, self.email, self.phone_number, self.method, self.options, self.collection_weeks, self.collection_days, self.datetime, self.sent, self.notes)


schedule = BlockingScheduler()
numToDays = ['', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']


def writeMessageLog(session, message_type, method, email=None, phone_number=None, options=None, collection_weeks=None, collection_days=None, sent=False, notes=None):
    messageLog = MessageLog(message_type=message_type, method=method, email=email, phone_number=phone_number, options=options, collection_weeks=collection_weeks, collection_days=collection_days, datetime=datetime, sent=sent, notes=notes)
    session.add(messageLog)
    session.commit()


def writeLog(session, user, message):
    logs = Logs(user=user, datetime=getCurrentDateTime(), notes=message)
    session.add(logs)
    session.commit()


def findAlerts(session, alertDateTime):
    return session.query(ScheduledAlerts).filter(ScheduledAlerts.datetime <= alertDateTime, ScheduledAlerts.sent==False).all()


def findSubscriptions(session, options, weeks, days):
    queryOptions = or_( *[Subscription.opt_in.like("%" + x + "%") for x in options] )
    q = session.query(Subscription).filter(queryOptions)
    
    if weeks:
        queryWeeks = or_( *[Subscription.schedule==x for x in weeks] )
        q = q.filter(queryWeeks)
    
    if days:
        queryDays = or_( *[Subscription.collection_days.like("%" + x + "%") for x in days] )
        q = q.filter(queryDays)
    
    return q.all()


def findCurrentActiveTextSubscriptions(session, options, hour, days=""):
    queryOptions = or_( *[Subscription.opt_in.like("%" + x + "%") for x in options] )
    q = session.query(Subscription).filter(queryOptions)
    if days:
        queryDays = or_( *[Subscription.collection_days.like("%" + x + "%") for x in days] )
        q = q.filter(queryDays)
    q = q.filter(and_(Subscription.text_number_active==True))
    q = q.filter(and_(Subscription.notification_time==hour))
    return q.all()

def findCurrentActiveEmailSubscriptions(session, options, hour, days=""):
    queryOptions = or_( *[Subscription.opt_in.like("%" + x + "%") for x in options] )
    q = session.query(Subscription).filter(queryOptions)
    if days:
        queryDays = or_( *[Subscription.collection_days.like("%" + x + "%") for x in days] )
        q = q.filter(queryDays)
    q = q.filter(and_(Subscription.email_active==True))
    q = q.filter(and_(Subscription.notification_time==hour))
    return q.all()


def findCurrentActiveCallSubscriptions(session, options, hour, days=""):
    queryOptions = or_( *[Subscription.opt_in.like("%" + x + "%") for x in options] )
    q = session.query(Subscription).filter(queryOptions)
    if days:
        queryDays = or_( *[Subscription.collection_days.like("%" + x + "%") for x in days] )
        q = q.filter(queryDays)
    q = q.filter(and_(Subscription.call_number_active==True))
    q = q.filter(and_(Subscription.notification_time==hour))
    return q.all()


def todayWeekandYear():
    todayWeek = date.today().strftime("%U")
    todayYear = date.today().year
    if date.today().month == 12 and date.today().day == 31:
        todayWeek = "00"
        todayYear += 1
    return todayWeek, todayYear


def holidayThisWeek():
    """
    Read in stat holidays file
    
    Return holidays occurring within the current week

    """

    statFile = open(config.DATA_STAT_HOLIDAYS)
    holiday = {}
    holiday['isHoliday'] = False

    todayWeek, todayYear = todayWeekandYear()
    for line in statFile:
        statDate = datetime.strptime(line.strip() , '%d/%m/%Y').date()

        statWeek = statDate.strftime("%U")
        
        if statWeek == todayWeek and statDate.year == todayYear:
            logger.debug("This is a stat holiday week: %s, today: %s" % (statDate, date.today()))
            holiday['isHoliday'] = True
            holiday['dayNum'] = (statDate.isoweekday() % 7) + 1
            break
    return holiday


def eventsThisWeek():
    """
    Read in special events file
    
    Return events occurring within the current week

    """

    specialEvents = generateSeasonalEvents()
    events = []
    event = {'isEvent': False,
             'dayNum': None,
             'title': None,
             'startDate': None,
             'endDate': None,
             'description': None}
    
    for line in specialEvents:
        startDate = datetime.strptime(line[1].strip() , '%Y-%m-%d').date()
        eventWeek = startDate.strftime("%U")
        if eventWeek == date.today().strftime("%U") and startDate.year == date.today().year:
            event['isEvent'] = True
            event['dayNum'] = (startDate.isoweekday() % 7) + 1
            event['title'] = line[0]
            event['startDate'] = startDate
            event['endDate'] = datetime.strptime(line[2].strip() , '%Y-%m-%d').date()
            event['description'] = line[3]
            events.append(event.copy())
    return events


def contactEventUsers(session, hour, event): 
    """
    Send msg to user given their contact methods 

    """

    myTwilioContact = TwilioContact(session, writeMessageLog, logger)
    myEmailContact = EmailContact(session, writeMessageLog, logger)

    notificationType = '3'
    textNumbers = findCurrentActiveTextSubscriptions(session, notificationType, hour)
    callNumbers = findCurrentActiveCallSubscriptions(session, notificationType, hour)
    emails = findCurrentActiveEmailSubscriptions(session, notificationType, hour)
    
    textNumbers = removeDuplicates(textNumbers)
    callNumbers = removeDuplicates(callNumbers)
    emails = removeDuplicates(emails)
    
    logger.info("Sending event notifications at %d to %d text users, %d call users, %d email users" % (hour, len(textNumbers), len(callNumbers), len(emails)))
  
    for number in textNumbers:
        if event['startDate'] != event['endDate']: #Multi Day event
            msg = getSetting("SpecialMultipleDayMessage", "text").format(event['title'], event['startDate'], event['endDate'], event['description'])
        else: # Single Days event
            msg = getSetting("SpecialSingleDayMessage", "text").format(event['startDate'], event['title'],event['description'])
        
        myTwilioContact.sendTwilioEventText(number.text_phone_number, msg, options=notificationType)
  
    for number in callNumbers:
        if event['startDate'] != event['endDate']: #Multi Day event
            msg = getSetting("SpecialMultipleDayMessage", "call").format(event['title'], event['startDate'], event['endDate'], event['description'])
        else: # Single Days event
            msg = getSetting("SpecialSingleDayMessage", "call").format(event['startDate'], event['title'], event['description'])

        myTwilioContact.sendTwilioEventCall(number.call_phone_number, msg, options=notificationType)
  
    for email in emails:
        if event['startDate'] != event['endDate']: #Multi Day event
            msg = getSetting("SpecialMultipleDayMessage", "email").format(event['title'], event['startDate'], event['endDate'], event['description'])
        else: # Single Days event
            msg = getSetting("SpecialSingleDayMessage", "email").format(event['startDate'], event['title'], event['description'])

        myEmailContact.sendEventEmail(email.email, 'Special Event Reminder!', msg, options=notificationType)
     
    writeLog(session, "system", "Sent event notifications at %d to %d text users, %d call users, %d email users" % (hour, len(textNumbers), len(callNumbers), len(emails)))


def determineCart(schedule):
    
    if not schedule:
        return None
    cartList = schedule.strip().split(';') # -> e.g. ['L','O','S']
    cartColors = None
    if 'L' in cartList and 'R' in cartList: # week Z pickups
        cartColors = 'BLUE, GREY and GREEN carts'
    elif 'L' in cartList:
        cartColors = 'GREY and GREEN carts'
    elif 'R' in cartList:
        cartColors = 'BLUE and GREEN carts'
        
    return cartColors

            
def readScheduleFile(scheduleFile):
    with open(scheduleFile) as f:
        readFile = [line.strip().split(' - ') for line in f]
    return readFile
    
    
def determineCartSchedule():
    
    scheduleAFile = readScheduleFile(config.DATA_WEEK_A_SCHEDULE)
    scheduleBFile = readScheduleFile(config.DATA_WEEK_B_SCHEDULE)
    scheduleZFile = readScheduleFile(config.DATA_WEEK_Z_SCHEDULE)
    
    weekAPickup = None
    weekBPickup = None
    weekZPickup = None
    
    todayWeek, todayYear = todayWeekandYear()
    for x, y in scheduleAFile:
        thisDate = datetime.strptime(x,'%d/%m/%Y').date()
        thisWeek = thisDate.strftime("%U")
        if thisWeek == todayWeek and thisDate.year == todayYear:
            weekAPickup = y
            break

    for x, y in scheduleBFile:
        thisDate = datetime.strptime(x,'%d/%m/%Y').date()
        thisWeek = thisDate.strftime("%U")
        if thisWeek == todayWeek and thisDate.year == todayYear:
            weekBPickup = y
            break

    for x, y in scheduleZFile:
        thisDate = datetime.strptime(x,'%d/%m/%Y').date()
        thisWeek = thisDate.strftime("%U")
        if thisWeek == todayWeek and thisDate.year == todayYear:
            weekZPickup = y
            break
    
    weekACart = determineCart(weekAPickup)
    weekBCart = determineCart(weekBPickup)
    weekZCart = determineCart(weekZPickup)
        
    return {'Week A': weekACart, 'Week B': weekBCart, 'Week Z': weekZCart}
    
        
def contactUsers(session, dayToFind, messageType, hour):
    """
    Define a context processor for merging flask-admin's 
    template context into the flask-security views.

    """

    myTwilioContact = TwilioContact(session, writeMessageLog, logger)
    myEmailContact = EmailContact(session, writeMessageLog, logger)

    if messageType=='carts':
        notificationType = '1'
    else:
        notificationType = '2'
        
    cartSchedule = determineCartSchedule()
    
    textNumbers = findCurrentActiveTextSubscriptions(session, notificationType, hour, days=dayToFind)
    callNumbers = findCurrentActiveCallSubscriptions(session, notificationType, hour, days=dayToFind)
    emails = findCurrentActiveEmailSubscriptions(session, notificationType, hour, days=dayToFind)
    
    textNumbers = removeDuplicates(textNumbers)
    callNumbers = removeDuplicates(callNumbers)
    emails = removeDuplicates(emails)
    
    logger.info("Sending regular notifications at %d to %d text users, %d call users, %d email users" % (hour, len(textNumbers), len(callNumbers), len(emails)))
    
    for number in textNumbers:
        sched = number.schedule
        carts = cartSchedule[sched]
        if messageType == 'stat' :
            msg = getSetting("StatHolidayMessage", "text").format(carts, number.address, (numToDays[(int(dayToFind) % 8) + 1]))
            myTwilioContact.sendTwilioSubscriptionText(number.text_phone_number, msg, options=notificationType, weeks=sched, days=dayToFind)
        else:
            msg = getSetting("ScheduledMessage", "text").format(number.address, (numToDays[(int(dayToFind) % 8)]), carts)
            myTwilioContact.sendTwilioSubscriptionText(number.text_phone_number, msg, options=notificationType, weeks=sched, days=dayToFind)
        
    for number in callNumbers:
        sched = number.schedule
        carts = cartSchedule[sched]
        if messageType == 'stat' :
            msg = getSetting("StatHolidayMessage", "call").format(carts, number.address, (numToDays[(int(dayToFind) % 8) + 1]))
            myTwilioContact.sendTwilioSubscriptionCall(number.call_phone_number, msg, options=notificationType, weeks=sched, days=dayToFind)
        else:
            msg = getSetting("ScheduledMessage", "call").format(number.address, (numToDays[(int(dayToFind) % 8)]), carts)
            myTwilioContact.sendTwilioSubscriptionCall(number.call_phone_number, msg, options=notificationType, weeks=sched, days=dayToFind)
               
    for email in emails:
        sched = email.schedule
        carts = cartSchedule[sched]
        if messageType == 'stat' :
            msg = getSetting("StatHolidayMessage", "email").format(carts, email.address, (numToDays[(int(dayToFind) % 8) + 1]))
            myEmailContact.sendSubscriptionEmail(email.email, 'Statutory Holiday Reminder!', msg, options=notificationType, weeks=sched, days=dayToFind)
        else:
            msg = getSetting("ScheduledMessage", "email").format(email.address, (numToDays[(int(dayToFind) % 8)]), carts)
            myEmailContact.sendSubscriptionEmail(email.email, 'Garbage Collection Reminder!', msg, options=notificationType, weeks=sched, days=dayToFind)
        
    if len(textNumbers)> 0 or len(callNumbers) > 0 or len(emails) > 0:
        writeLog(session, "system", "Sent regular notifications at %d to %d text users, %d call users, %d email users" % (hour, len(textNumbers), len(callNumbers), len(emails)))
    
    
def checkSchedule(sched):
    """
    Based on given schedule decide what carts are to be put out 

    """

    weekNumber = date.today().isocalendar()[1]
    if sched == 'Week A':
        if weekNumber % 2 == 0:
            carts = 'BLUE and GREEN carts'
        else:
            carts = 'GREY and GREEN carts'
    elif sched == 'Week B':
        if weekNumber % 2 == 0:
            carts = 'GREY and GREEN carts'
        else:
            carts = 'BLUE and GREEN carts'
    elif sched == 'Week Z':
        carts = 'BLUE, GREY and GREEN carts'
    
    return carts


def getNotificationDates():
    """
    Determine the day # of the week for today and tomorrows date 
    
    Get the current hour

    """

    today = date.today()
    tomorrowDate = today + timedelta(days=1)
    dayToday = (today.isoweekday() % 7) + 1
    dayTomorrow = (tomorrowDate.isoweekday() % 7) + 1
    currentHour=datetime.now().hour
    return dayToday, dayTomorrow, currentHour


def getFormattedCurrentDateTime():
    """
    Get current date and format 

    """

    return datetime.now().strftime("%Y-%m-%d %H:%M:00")


@schedule.scheduled_job('interval', minutes=1, max_instances=1)
def sendScheduledAlerts():
    """
    Runs on schedule every minute
    
    Check for scheduled alerts and send to matching subscriptions 

    """


    try:
        
        session = db()
        myTwilioContact = TwilioContact(session, writeMessageLog, logger)
       
        #Find any alerts scheduled for this day and time     
        currentDateTime = getFormattedCurrentDateTime()
        alerts = findAlerts(session,currentDateTime)
                       
        if not alerts:
            logger.info("No scheduled alerts to send at %s" % currentDateTime)
            return None
           
        for alert in alerts:
            
            days = []
            weeks = []
            options = list(alert.options.replace("0", ""))
            if alert.collection_weeks:
                weeks = alert.collection_weeks.split(";")
            if alert.collection_days:
                days = alert.collection_days.split(";")
           
            #Find all subscriptions matching criteria
            subscriptions = findSubscriptions(session, options, weeks, days)
            
            alerts_sent = 0
            for sub in subscriptions:
                    if alert.type=="text" and sub.text_number_active and sub.text_phone_number:
                        myTwilioContact.sendTwilioAlertText(sub.text_phone_number, alert.message, options=alert.options, weeks=alert.collection_weeks, days=alert.collection_days)
                        alerts_sent +=1
    
                    elif alert.type=="call" and sub.call_number_active and sub.call_phone_number:
                        myTwilioContact.sendTwilioAlertCall(sub.call_phone_number, alert.message, options=alert.options, weeks=alert.collection_weeks, days=alert.collection_days)
                        alerts_sent +=1
            
            #Update alert to sent = True
            alert.sent = True
            session.commit()
            
            writeLog(session, "system", "Scheduled alert processed sent to %d users: %s" % (alerts_sent, alert.message)) 
            logger.info("Sent scheduled alert to %d users" % (alerts_sent))
            
            
        session.commit()
        
    except Exception as e:
        #logger.critical("Exception: %s" % e)
        logger.critical("Traceback: %s" % traceback.format_exc())
        
    finally:
        session.close()


@schedule.scheduled_job('cron', minute=0)
def sendNotifications():
    """
    Run on schedule at the start of every hour
    
    Send notifications based on the current date and time
    
    Account for a stat holiday occurring within the current week
     
    Send notification for special events that are happening tomorrow
    

    """

    try:
        
        #Initialize DB session
        session = db()
        
        #Setup current days and hour
        dayToday, dayTomorrow, currentHour = getNotificationDates()

        #Get holidays and events occurring this week 
        holiday = holidayThisWeek()
        events = eventsThisWeek()
        
        #If there is a holiday this week and doesn't fall on a Sunday or Saturday
        if holiday['isHoliday'] and holiday['dayNum'] > 1 and holiday['dayNum'] < 7:

            if holiday['dayNum'] > dayTomorrow:
                contactUsers(session, str(dayTomorrow), 'carts', currentHour) #regular contact, stat this week doesn't affect these users
            elif holiday['dayNum'] == dayTomorrow:
                contactUsers(session, str(dayTomorrow), 'stat', currentHour) #stat is tomorrow
            else:
                contactUsers(session, str(dayTomorrow), 'stat', currentHour) #stat has already happened, delay everything by one
                #contactUsers(str(dayToday), 'carts', hour)
        else:
            contactUsers(session, str(dayTomorrow), 'carts', currentHour)
     
        # Send notifications for each special event that may be occurring tomorrow
        if events:
            for event in events:
                if event['dayNum'] == dayTomorrow:
                    contactEventUsers(session, currentHour, event)

    except Exception as e:
        #logger.critical("Exception: %s" % e)
        logger.critical("Traceback: %s" % traceback.format_exc())   
        
    finally:
        session.close()
        

def startScheduler():
    """
    Start any function that is decorated

    """
    schedule.start()
