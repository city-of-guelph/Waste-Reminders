from flask_security import UserMixin, RoleMixin
from sqlalchemy.sql import and_, or_
from app import db, datetime


def getCurrentDateTime():
    return datetime.now()

# Define models
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(50), unique=True, index=True, nullable=False)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __str__(self):
        return self.user_name


class Logs(db.Model):
    __tablename__= "logs"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(50), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.String(1000), nullable=False)
    
    def __init__(self, user="", datetime="", notes=""):
        self.user = user
        self.datetime = datetime
        self.notes = notes

    def __repr__(self):
        return '%r %r %r' % (self.user, self.datetime, self.notes)

    def writeLog(self, user, message):
        logs = Logs(user=user, datetime=getCurrentDateTime(), notes=message)
        db.session.add(logs)
        db.session.commit()


class ScheduledAlerts(db.Model):
    __tablename__= "alerts"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(50), nullable=False)
    options = db.Column(db.String(10),nullable=False)
    collection_weeks = db.Column(db.String(50), nullable=False)
    collection_days = db.Column(db.String(20), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    sent = db.Column(db.Boolean)
    message = db.Column(db.String(1000), nullable=False)
    
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

    def addAlert(self, user, options, collection_weeks, collection_days, datetime, type, message):
        alert = ScheduledAlerts(user=user, options=options, collection_weeks=collection_weeks, collection_days=collection_days, datetime=datetime, type=type, message=message)
        db.session.add(alert)
        db.session.commit()


class Subscription(db.Model):
    __tablename__ = "subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), nullable=False)
    address_id = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(255),nullable=True)
    email_active = db.Column(db.Boolean)
    opt_in = db.Column(db.String(10),nullable=False)
    call_phone_number = db.Column(db.String(10), nullable=True)
    call_number_active = db.Column(db.Boolean)
    text_phone_number = db.Column(db.String(10), nullable=True)
    text_number_active = db.Column(db.Boolean)
    collection_days = db.Column(db.String(20), nullable=False)
    schedule = db.Column(db.String(50), nullable=False)
    notification_time = db.Column(db.Integer,nullable=False)
    created = db.Column(db.DateTime, nullable=False)
    email_verification_code = db.Column(db.String(10),nullable=True)
    text_verification_code = db.Column(db.String(10),nullable=True)
    call_verification_code = db.Column(db.String(10),nullable=True)

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

    def addSubscription(self, address, addressId, email, optionalComms, callPhoneNumber, textPhoneNumber, collectionDays, schedule, notificationTime, emailVerificationCode, textVerificationCode, callVerificationCode, emailActive=False, textActive=False, callActive=False):
        # changing the data to DB-friendly format, adding the user
        if callPhoneNumber == '':
            callPhoneNumber = None
        if textPhoneNumber == '':
            textPhoneNumber = None
        if email == '':
            email = None
        daysString = ''.join(collectionDays)
        sub = Subscription(address=address, addressId=addressId, email=email, emailActive=emailActive, optin=optionalComms, callPhoneNumber=callPhoneNumber, callNumberActive=callActive, 
                                textPhoneNumber=textPhoneNumber, textNumberActive=textActive, collectiondays=daysString, schedule=schedule, notificationTime=notificationTime, 
                                created=getCurrentDateTime(), emailVerificationCode=emailVerificationCode, textVerificationCode=textVerificationCode, callVerificationCode=callVerificationCode)
        db.session.add(sub)
        db.session.commit()


    def updateScheduleByAddressId(self, addressId, schedule, collectionDays):
        subscription = Subscription.query.filter_by(address_id=addressId).all()
        for sub in subscription: 
            sub.schedule = schedule
            sub.collection_days = collectionDays
            db.session.commit()
        

    def findActiveEmailSubscriptions(self, options, weeks, days):
        queryOptions = or_( *[Subscription.opt_in.like("%" + x + "%") for x in options] )
        queryWeeks = or_( *[Subscription.schedule==x for x in weeks] )
        queryDays = or_( *[Subscription.collection_days.like("%" + x + "%") for x in days] )
        q = Subscription.query.filter(queryOptions)
        q = q.filter(queryWeeks)
        q = q.filter(queryDays)
        q = q.filter(and_(Subscription.email_active==True))
        return q.all()


    def findActiveTextSubscriptions(self, options, weeks, days):
        queryOptions = or_( *[Subscription.opt_in.like("%" + x + "%") for x in options] )
        queryWeeks = or_( *[Subscription.schedule==x for x in weeks] )
        queryDays = or_( *[Subscription.collection_days.like("%" + x + "%") for x in days] )
        q = Subscription.query.filter(queryOptions)
        q = q.filter(queryWeeks)
        q = q.filter(queryDays)
        q = q.filter(and_(Subscription.text_number_active==True))
        return q.all()


    def findActiveCallSubscriptions(self, options, weeks, days):
        queryOptions = or_( *[Subscription.opt_in.like("%" + x + "%") for x in options] )
        queryWeeks = or_( *[Subscription.schedule==x for x in weeks] )
        queryDays = or_( *[Subscription.collection_days.like("%" + x + "%") for x in days] )
        q = Subscription.query.filter(queryOptions)
        q = q.filter(queryWeeks)
        q = q.filter(queryDays)
        q = q.filter(and_(Subscription.call_number_active==True))
        return q.all()
  
        
    def updateActivateSub(self, email, emailActive, emailVerificationCode, textPhoneNumber, textActive, textVerificationCode, callPhoneNumber, callActive, callVerificationCode):
        sub = Subscription.query.filter_by(email=email, email_verification_code=emailVerificationCode, text_phone_number=textPhoneNumber, text_verification_code=textVerificationCode, 
                                        call_phone_number=callPhoneNumber, call_verification_code=callVerificationCode).first()
        sub.email_active = emailActive
        sub.text_number_active = textActive
        sub.call_number_active = callActive
        db.session.commit()
    
    
    def unsubscribeEmail(self, address, email):
        sub = Subscription.query.filter_by(email=email, email_active=True, address=address).first()
        if not sub:
            return "Subscribed email not found"
        sub.email_active = False
        try:
            db.session.commit()
        except Exception as e:
            return "Failed to unsubscribe email address"
    
    
    def unsubscribeText(self, address, textPhoneNumber):
        sub = Subscription.query.filter_by(text_phone_number=textPhoneNumber, text_number_active=True, address=address).first()
        if not sub:
            return "Subscribed text number not found"
        sub.text_number_active = False
        try:
            db.session.commit()
        except Exception as e:
            return "Failed to unsubscribe text number"
    
        
    def unsubscribeCall(self, address, callPhoneNumber):
        sub = Subscription.query.filter_by(call_phone_number=callPhoneNumber, call_number_active=True, address=address).first()
        if not sub:
            return "Subscribed call number not found"
        sub.call_number_active = False
        try:
            db.session.commit()
        except Exception as e:
            return "Failed to unsubscribe call number"


class MessageLog(db.Model):
    __tablename__= "message_log"
    id = db.Column(db.Integer, primary_key=True)
    message_type = db.Column(db.String(20), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(255))
    phone_number = db.Column(db.String(10))
    options = db.Column(db.String(10))
    collection_weeks = db.Column(db.String(50))
    collection_days = db.Column(db.String(20))
    datetime = db.Column(db.DateTime, nullable=False)
    sent = db.Column(db.Boolean)
    notes = db.Column(db.String(1000))
    
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
    
def writeMessageLog(db, message_type, method, email=None, phone_number=None, options=None, collection_weeks=None, collection_days=None, sent=False, notes=None):
    messageLog = MessageLog(message_type=message_type, method=method, email=email, phone_number=phone_number, options=options, collection_weeks=collection_weeks, collection_days=collection_days, datetime=datetime, sent=sent, notes=notes)
    db.session.add(messageLog)
    db.session.commit()
