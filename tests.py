import os
import unittest
import reminders
import mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date


from config import basedir
from app import app, db, ScheduledAlerts, Subscription

import flask


class MyTestClass(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        pass
    
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    
    def setUp(self):
        # creates a test client
        self.app = app.test_client()
        
        # propagate the exceptions to the test client
        self.app.testing = True 
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
            os.path.join(basedir, 'test.db')
        db.create_all()
        self.db = db
        
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        Session = sessionmaker(bind=engine)
        self.db_reminders = Session()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
    

    def test_home_status(self):
        result = self.app.get('/')
        self.assertEqual(result.status_code, 200)
        
    def test_invalid_address(self):
        result = self.app.post('/getInfo/', data=dict(
                address="123 Bad Street"), follow_redirects=True)
        self.assertEqual(result.status_code, 200)
        assert "address is unavailable" in result.data

    def test_valid_address(self):
        with self.app as c:
            result = c.post('/getInfo/', data=dict(
                    address="1 CARDEN ST"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(flask.session['address'], "1 CARDEN ST")
            self.assertEqual(flask.session['addressId'], "5338")
            self.assertEqual(flask.session['schedule'], "Week Z")
            self.assertIsNotNone(flask.session['collectionDay'])
            self.assertIsNotNone(flask.session['collectionDayNum'])
            self.assertIsNotNone(flask.session['pickupDates'])
            assert "Sign up for reminders" in result.data
        

    def test_invalid_signup(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "1 CARDEN ST"
            result = self.app.post('/signup/', data=dict(
                        email="", text="", call=""), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Please enter at least one method of contact" in result.data


    def test_invalid_text_phone_signup(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "1 CARDEN ST"
            result = self.app.post('/signup/', data=dict(
                        email="", text="123456789", call=""), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Please enter a valid phone number" in result.data


    def test_invalid_call_phone_signup(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "1 CARDEN ST"
            result = self.app.post('/signup/', data=dict(
                        email="", text="", call="123456789"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Please enter a valid phone number" in result.data
        
        
    def test_valid_signup(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "1 CARDEN ST"
            result = c.post('/signup/', data=dict(
                        email="test@test.com", text="5195555555", call="5195555555"), follow_redirects=True)
            self.assertEqual(flask.session['emailAddress'], "test@test.com")
            self.assertEqual(flask.session['textPhoneNumber'], "5195555555")
            self.assertEqual(flask.session['callPhoneNumber'], "5195555555")
            self.assertEqual(result.status_code, 200)
            assert "Send verification" in result.data


    def test_session_timeout_signup(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = None
            result = c.post('/signup/', data=dict(
                        email="test@test.com", text="5195555555", call="5195555555"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Your session has expired" in result.data
    
    
    def test_invalid_notifications(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "1 CARDEN ST"
            result = self.app.post('/confirmation/', data=dict(
                        time="7"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Please select at least one notification type" in result.data    
    

    @mock.patch("smtplib.SMTP")
    @mock.patch('app.views.generateValidationCode')
    @mock.patch('app.db')
    def test_valid_notifications(self, db_mock, mock_validationCode, mock_smtp):
        db_mock.return_value = self.db
        mock_validationCode.return_value = "12345"
        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "1 CARDEN ST"
                sess['addressId'] = "5338"
                sess['emailAddress'] = "test@test.com"
                sess['textPhoneNumber'] = "5195555555"
                sess['callPhoneNumber'] = "5195555555"
                sess['collectionDayNum'] = ["2"]
                sess['schedule'] = "Week A"
                sess['yearSched'] = [[['2016-01-04', u'#0099FF'], ['2016-01-05', u'#0099FF']], [['BLUE'], ['GREY']]]
            result = self.app.post('/confirmation/', data=dict(
                        optin1="1", optin2="2", optin3="3", time="7"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Verify" in result.data
            
            sub = Subscription.query.first()
            self.assertEqual(sub.address, "1 CARDEN ST")
            self.assertEqual(sub.address_id, "5338")
            self.assertEqual(sub.email_active, False)
            self.assertEqual(sub.email, "test@test.com")
            self.assertEqual(sub.opt_in, "12300")
            self.assertEqual(sub.call_phone_number, "5195555555")
            self.assertEqual(sub.call_number_active, False)
            self.assertEqual(sub.text_phone_number, "5195555555")
            self.assertEqual(sub.text_number_active, False)
            self.assertEqual(sub.collection_days, "2")
            self.assertEqual(sub.schedule, "Week A")
            self.assertEqual(sub.notification_time, 7)
            self.assertEqual(sub.email_verification_code, "112345")
            self.assertEqual(sub.text_verification_code, "212345")
            self.assertEqual(sub.call_verification_code, "312345")
            mock_smtp.return_value.sendmail.assert_called_once
      
   
    def test_session_timeout_notifications(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = None
            result = self.app.post('/confirmation/', data=dict(
                        optin1="1", optin2="2", optin3="3", time="7"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Your session has expired" in result.data


    @mock.patch('app.db')
    def test_invalid_email_confirm_signup(self, db_mock):
        db_mock.return_value = self.db
        
        sub = Subscription(address="123 Testing St", addressId = "123", optin="12345", email="test@test.com", emailActive=False, textPhoneNumber="5195555555", textNumberActive=False, callPhoneNumber="5195555555", callNumberActive=False, collectiondays="2", schedule="Week A", notificationTime=12, emailVerificationCode="E12345", textVerificationCode="T12345", callVerificationCode="C12345")
        self.db.session.add(sub)
        self.db.session.commit()

        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "123 Testing St"
                sess['scheduledTime'] = 12
                sess['schedule'] = "Week A"
                sess['collectionDayNum'] = ["2"]
                sess['emailAddress'] = "test@test.com"
                sess['textPhoneNumber'] = "5195555555"
                sess['callPhoneNumber'] = "5195555555"
                sess['emailVerificationCode'] = "E12345"
                sess['textVerificationCode'] = "T12345"
                sess['callVerificationCode'] = "C12345"
            result = self.app.post('/verify/', data=dict(
                       emailCode="INVALID", textCode="T12345", callCode="C12345"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            #assert "Verify" in result.data
            
            sub = Subscription.query.first()
            self.assertEqual(sub.address, "123 Testing St")
            self.assertEqual(sub.address_id, "123")
            self.assertEqual(sub.email_active, False)
            self.assertEqual(sub.email, "test@test.com")
            self.assertEqual(sub.opt_in, "12345")
            self.assertEqual(sub.call_phone_number, "5195555555")
            self.assertEqual(sub.call_number_active, False)
            self.assertEqual(sub.text_phone_number, "5195555555")
            self.assertEqual(sub.text_number_active, False)
            self.assertEqual(sub.collection_days, "2")
            self.assertEqual(sub.schedule, "Week A")
            self.assertEqual(sub.notification_time, 12)
            self.assertEqual(sub.email_verification_code, "E12345")
            self.assertEqual(sub.text_verification_code, "T12345")
            self.assertEqual(sub.call_verification_code, "C12345")
            assert "The email verification code entered is not correct" in result.data


    @mock.patch('app.db')
    def test_invalid_text_confirm_signup(self, db_mock):
        db_mock.return_value = self.db
        
        sub = Subscription(address="123 Testing St", addressId = "123", optin="12345", email="test@test.com", emailActive=False, textPhoneNumber="5195555555", textNumberActive=False, callPhoneNumber="5195555555", callNumberActive=False, collectiondays="2", schedule="Week A", notificationTime=12, emailVerificationCode="E12345", textVerificationCode="T12345", callVerificationCode="C12345")
        self.db.session.add(sub)
        self.db.session.commit()

        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "123 Testing St"
                sess['scheduledTime'] = 12
                sess['schedule'] = "Week A"
                sess['collectionDayNum'] = ["2"]
                sess['emailAddress'] = "test@test.com"
                sess['textPhoneNumber'] = "5195555555"
                sess['callPhoneNumber'] = "5195555555"
                sess['emailVerificationCode'] = "E12345"
                sess['textVerificationCode'] = "T12345"
                sess['callVerificationCode'] = "C12345"
            result = self.app.post('/verify/', data=dict(
                       emailCode="E12345", textCode="INVALID", callCode="C12345"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            #assert "Verify" in result.data
            
            sub = Subscription.query.first()
            self.assertEqual(sub.address, "123 Testing St")
            self.assertEqual(sub.address_id, "123")
            self.assertEqual(sub.email_active, False)
            self.assertEqual(sub.email, "test@test.com")
            self.assertEqual(sub.opt_in, "12345")
            self.assertEqual(sub.call_phone_number, "5195555555")
            self.assertEqual(sub.call_number_active, False)
            self.assertEqual(sub.text_phone_number, "5195555555")
            self.assertEqual(sub.text_number_active, False)
            self.assertEqual(sub.collection_days, "2")
            self.assertEqual(sub.schedule, "Week A")
            self.assertEqual(sub.notification_time, 12)
            self.assertEqual(sub.email_verification_code, "E12345")
            self.assertEqual(sub.text_verification_code, "T12345")
            self.assertEqual(sub.call_verification_code, "C12345")
            assert "The text msg verification code entered is not correct" in result.data


    @mock.patch('app.db')
    def test_invalid_call_confirm_signup(self, db_mock):
        db_mock.return_value = self.db
        
        sub = Subscription(address="123 Testing St", addressId = "123", optin="12345", email="test@test.com", emailActive=False, textPhoneNumber="5195555555", textNumberActive=False, callPhoneNumber="5195555555", callNumberActive=False, collectiondays="2", schedule="Week A", notificationTime=12, emailVerificationCode="E12345", textVerificationCode="T12345", callVerificationCode="C12345")
        self.db.session.add(sub)
        self.db.session.commit()

        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "123 Testing St"
                sess['scheduledTime'] = 12
                sess['schedule'] = "Week A"
                sess['collectionDayNum'] = ["2"]
                sess['emailAddress'] = "test@test.com"
                sess['textPhoneNumber'] = "5195555555"
                sess['callPhoneNumber'] = "5195555555"
                sess['emailVerificationCode'] = "E12345"
                sess['textVerificationCode'] = "T12345"
                sess['callVerificationCode'] = "C12345"
            result = self.app.post('/verify/', data=dict(
                       emailCode="E12345", textCode="T12345", callCode="INVALID"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            #assert "Verify" in result.data
            
            sub = Subscription.query.first()
            self.assertEqual(sub.address, "123 Testing St")
            self.assertEqual(sub.address_id, "123")
            self.assertEqual(sub.email_active, False)
            self.assertEqual(sub.email, "test@test.com")
            self.assertEqual(sub.opt_in, "12345")
            self.assertEqual(sub.call_phone_number, "5195555555")
            self.assertEqual(sub.call_number_active, False)
            self.assertEqual(sub.text_phone_number, "5195555555")
            self.assertEqual(sub.text_number_active, False)
            self.assertEqual(sub.collection_days, "2")
            self.assertEqual(sub.schedule, "Week A")
            self.assertEqual(sub.notification_time, 12)
            self.assertEqual(sub.email_verification_code, "E12345")
            self.assertEqual(sub.text_verification_code, "T12345")
            self.assertEqual(sub.call_verification_code, "C12345")
            assert "The phone call verification code entered is not correct" in result.data


    @mock.patch("smtplib.SMTP")
    @mock.patch('app.db')
    def test_valid_confirmed_signup(self, db_mock, mock_smtp):
        db_mock.return_value = self.db
        
        sub = Subscription(address="123 Testing St", addressId = "123", optin="12345", email="test@test.com", emailActive=False, textPhoneNumber="5195555555", textNumberActive=False, callPhoneNumber="5195555555", callNumberActive=False, collectiondays="2", schedule="Week A", notificationTime=12, emailVerificationCode="E12345", textVerificationCode="T12345", callVerificationCode="C12345")
        self.db.session.add(sub)
        self.db.session.commit()

        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = "123 Testing St"
                sess['scheduledTime'] = 12
                sess['schedule'] = "Week A"
                sess['collectionDayNum'] = ["2"]
                sess['emailAddress'] = "test@test.com"
                sess['textPhoneNumber'] = "5195555555"
                sess['callPhoneNumber'] = "5195555555"
                sess['emailVerificationCode'] = "E12345"
                sess['textVerificationCode'] = "T12345"
                sess['callVerificationCode'] = "C12345"
            result = self.app.post('/verify/', data=dict(
                       emailCode="E12345", textCode="T12345", callCode="C12345"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            #assert "Verify" in result.data
            
            sub = Subscription.query.first()
            self.assertEqual(sub.address, "123 Testing St")
            self.assertEqual(sub.address_id, "123")
            self.assertEqual(sub.email_active, True)
            self.assertEqual(sub.email, "test@test.com")
            self.assertEqual(sub.opt_in, "12345")
            self.assertEqual(sub.call_phone_number, "5195555555")
            self.assertEqual(sub.call_number_active, True)
            self.assertEqual(sub.text_phone_number, "5195555555")
            self.assertEqual(sub.text_number_active, True)
            self.assertEqual(sub.collection_days, "2")
            self.assertEqual(sub.schedule, "Week A")
            self.assertEqual(sub.notification_time, 12)
            self.assertEqual(sub.email_verification_code, "E12345")
            self.assertEqual(sub.text_verification_code, "T12345")
            self.assertEqual(sub.call_verification_code, "C12345")
            assert "Congratulations" in result.data
            mock_smtp.return_value.sendmail.assert_called_once


    @mock.patch("smtplib.SMTP")
    @mock.patch('app.db')
    def test_session_timeout_confirmed_signup(self, db_mock, mock_smtp):
        db_mock.return_value = self.db
        
        sub = Subscription(address="123 Testing St", addressId = "123", optin="12345", email="test@test.com", emailActive=False, textPhoneNumber="5195555555", textNumberActive=False, callPhoneNumber="5195555555", callNumberActive=False, collectiondays="2", schedule="Week A", notificationTime=12, emailVerificationCode="E12345", textVerificationCode="T12345", callVerificationCode="C12345")
        self.db.session.add(sub)
        self.db.session.commit()

        with self.app as c:
            with c.session_transaction() as sess:
                sess['address'] = None
            result = self.app.post('/verify/', data=dict(
                       emailCode="E12345", textCode="T12345", callCode="C12345"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Your session has expired" in result.data


    def test_session_timeout_calendar(self):
        with self.app as c:
            result = c.get('/calendar/', follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Your session has expired" in result.data


    def test_valid_week_a_calendar(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['pickupDates'] = ['2016-04-18', '2016-04-25', '2016-05-02', '2016-05-09']
                sess['yearSched'] = [[['2016-04-18', u'#0099FF'], ['2016-04-25', u'#0099FF']], [['BLUE'], ['GREY']]]
                sess['schedule'] = "Week A"
                sess['address'] = "123 Testing St."

            result = c.get('/calendar/', follow_redirects=True)
            self.assertEqual(result.status_code, 200)


    def test_valid_week_b_calendar(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['pickupDates'] = ['2016-04-21', '2016-04-28', '2016-05-05', '2016-05-12']
                sess['yearSched'] = [[['2016-04-21', u'#0099FF'], ['2016-04-28', u'#0099FF']], [['BLUE'], ['GREY']]]
                sess['schedule'] = "Week B"
                sess['address'] = "123 Testing St."

            result = c.get('/calendar/', follow_redirects=True)
            self.assertEqual(result.status_code, 200)


    def test_session_timeout_calendar_download(self):
        with self.app as c:
            result = c.get('/download/', follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Your session has expired" in result.data


    def test_valid_week_a_calendar_download(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['pickupDates'] = ['2016-04-18', '2016-04-25', '2016-05-02', '2016-05-09']
                sess['yearSched'] = [[['2016-04-18', u'#0099FF'], ['2016-04-25', u'#0099FF']], [['BLUE'], ['GREY'], ['BLUE'], ['GREY']]]
                sess['schedule'] = "Week A"
                sess['address'] = "123 Testing St."

            result = c.get('/download/', follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            self.assertIsNotNone(result.data)
            
            
    def test_valid_week_b_calendar_download(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['pickupDates'] = ['2016-04-21', '2016-04-28', '2016-05-05', '2016-05-12']
                sess['yearSched'] = [[['2016-04-21', u'#0099FF'], ['2016-04-28', u'#0099FF']], [['BLUE'], ['GREY'], ['BLUE'], ['GREY']]]
                sess['schedule'] = "Week B"
                sess['address'] = "123 Testing St."

            result = c.get('/download/', follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            self.assertIsNotNone(result.data)
            
       
    def mock_singleDayEventThisWeek(self):
        return [{'isEvent': True,
             'dayNum': 2,
             'title': 'Mock Event',
             'startDate': '2016-01-01',
             'endDate': '2016-01-01',
             'description': 'Mocking a test event description'}]


    def mock_multiDayEventThisWeek(self):
        return [{'isEvent': True,
             'dayNum': 2,
             'title': 'Mock Multi Day Event',
             'startDate': '2016-01-01',
             'endDate': '2016-01-07',
             'description': 'Mocking a test multi day event description'}]
            
    
    @mock.patch("smtplib.SMTP")
    @mock.patch('reminders.db')
    @mock.patch('reminders.getNotificationDates')
    @mock.patch('reminders.holidayThisWeek')
    @mock.patch('reminders.eventsThisWeek')
    def test_send_regular_notifications_no_events(self, events_mock, holiday_mock, notification_dates_mock, db_mock, stmp_mock):
        holiday_mock.return_value = {'isHoliday': True, 'dayNum': 2}
        notification_dates_mock.return_value = 1, 2, 12
        db_mock.return_value = self.db_reminders
        events_mock.return_value = []
        
        sub = reminders.Subscription(address="123 Testing St", addressId = "123", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", optin="12345", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="2", schedule="Week A", notificationTime=12, )
        self.db_reminders.add(sub)
        reminders.sendNotifications()
        
        messageLog = self.db_reminders.query(reminders.MessageLog).first()
        self.assertEqual(messageLog.message_type, "Subscription")
        self.assertEqual(messageLog.sent, True)
        self.assertEqual(messageLog.method, "text")
        self.assertEqual(messageLog.phone_number, "5195555555")


    @mock.patch("smtplib.SMTP")
    @mock.patch('reminders.db')
    @mock.patch('reminders.getNotificationDates')
    @mock.patch('reminders.holidayThisWeek')
    @mock.patch('reminders.eventsThisWeek')
    def test_send_single_day_event_no_subscription(self, events_mock, holiday_mock, notification_dates_mock, db_mock, mock_smtp):
        holiday_mock.return_value = {'isHoliday': False, 'dayNum': None}
        notification_dates_mock.return_value = 1, 2, 12
        events_mock.return_value = self.mock_singleDayEventThisWeek()
        db_mock.return_value = self.db_reminders

        sub = reminders.Subscription(address="123 Testing St", addressId = "123", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", optin="00345", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="2", schedule="Week A", notificationTime=12, )
        self.db_reminders.add(sub)      
        reminders.sendNotifications()
        
        messageLog = self.db_reminders.query(reminders.MessageLog).first()
        self.assertEqual(messageLog.message_type, "Event")
        self.assertEqual(messageLog.sent, True)
        self.assertEqual(messageLog.method, "text")
        self.assertEqual(messageLog.phone_number, "5195555555")
        mock_smtp.return_value.sendmail.assert_called_once


    @mock.patch("smtplib.SMTP")
    @mock.patch('reminders.db')
    @mock.patch('reminders.getNotificationDates')
    @mock.patch('reminders.holidayThisWeek')
    @mock.patch('reminders.eventsThisWeek')
    def test_send_multi_day_event_no_holiday(self, events_mock, holiday_mock, notification_dates_mock, db_mock, mock_smtp):
        holiday_mock.return_value = {'isHoliday': False, 'dayNum': None}
        notification_dates_mock.return_value = 1, 2, 12
        events_mock.return_value = self.mock_multiDayEventThisWeek()
        db_mock.return_value = self.db_reminders

        sub = reminders.Subscription(address="123 Testing St", addressId = "123", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", optin="00345", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="2", schedule="Week A", notificationTime=12, )
        self.db_reminders.add(sub)      
        reminders.sendNotifications()
        
        messageLog = self.db_reminders.query(reminders.MessageLog).first()
        self.assertEqual(messageLog.message_type, "Event")
        self.assertEqual(messageLog.sent, True)
        self.assertEqual(messageLog.method, "text")
        self.assertEqual(messageLog.phone_number, "5195555555")
        mock_smtp.return_value.sendmail.assert_called_once


    @mock.patch('reminders.db')
    @mock.patch('reminders.getFormattedCurrentDateTime')
    def test_send_scheduled_alert_text(self, formatted_dateTime_mock, db_mock):
        formatted_dateTime_mock.return_value = "2016-01-02 12:01:00"
        db_mock.return_value = self.db_reminders

        alert = reminders.ScheduledAlerts(user="system", options="345", collection_weeks="Week A", collection_days="2", datetime=datetime(2016, 01, 02, 12, 00, 00), type="text", message="Test mock alert")
        self.db_reminders.add(alert)
        self.db_reminders.commit()
        
        sub = reminders.Subscription(address="123 Testing St", addressId = "123", textPhoneNumber="5195555555", optin="12345", textNumberActive=True, collectiondays="2", schedule="Week A", notificationTime=12, )
        self.db_reminders.add(sub)
        self.db_reminders.commit()              

        reminders.sendScheduledAlerts()
        
        alertSent = self.db_reminders.query(reminders.ScheduledAlerts).first()
        self.assertIsNotNone(alertSent)
        self.assertEqual(alertSent.sent, True)
        
        messageLog = self.db_reminders.query(reminders.MessageLog).first()
        self.assertEqual(messageLog.message_type, "Alert")
        self.assertEqual(messageLog.sent, True)
        self.assertEqual(messageLog.method, "text")
        self.assertEqual(messageLog.phone_number, "5195555555")
        
        
    @mock.patch('reminders.db')
    @mock.patch('reminders.getFormattedCurrentDateTime')
    def test_send_scheduled_alert_call(self, formatted_dateTime_mock, db_mock):
        formatted_dateTime_mock.return_value = "2016-01-02 12:01:00"
        db_mock.return_value = self.db_reminders

        alert = reminders.ScheduledAlerts(user="system", options="345", collection_weeks="", collection_days="", datetime=datetime(2016, 01, 02, 12, 00, 00), type="call", message="Test mock alert")
        self.db_reminders.add(alert)
        self.db_reminders.commit()
        
        sub = reminders.Subscription(address="123 Testing St", addressId = "123", callPhoneNumber="5195555555", optin="12345", callNumberActive=True, collectiondays="2", schedule="Week A", notificationTime=12, )
        self.db_reminders.add(sub)
        self.db_reminders.commit()              

        reminders.sendScheduledAlerts()
        
        alertSent = self.db_reminders.query(reminders.ScheduledAlerts).first()
        self.assertIsNotNone(alertSent)
        self.assertEqual(alertSent.sent, True)
        
        messageLog = self.db_reminders.query(reminders.MessageLog).first()
        self.assertEqual(messageLog.message_type, "Alert")
        self.assertEqual(messageLog.sent, True)
        self.assertEqual(messageLog.method, "call")
        self.assertEqual(messageLog.phone_number, "5195555555")

    
    @mock.patch('app.db')
    def test_email_alert(self, db_mock):
        db_mock.return_value = self.db
        sub = Subscription(address="123 Testing St", addressId = "123", optin="12345", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="2", schedule="Week A", notificationTime=14)
        self.db.session.add(sub)
        self.db.session.commit()

        with self.app as c:
            result = c.post('/broadcast/', data=dict(opt1=0, opt2=0, opt3=3, opt4=4, opt5=5,
                        alert_type="email", collectionWeek="Week A", collectionDay="2"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            self.assertIsNotNone(result.data)


    @mock.patch('app.db')
    def test_schedule_text_alert(self, db_mock):
        db_mock.return_value = self.db
        with self.app as c:
            result = c.post('/broadcast/', data=dict(opt1=0, opt2=0, opt3=3, opt4=4, opt5=5,
                        alert_type="text", textAlert="Testing a text alert", scheduledDate="01/01/2016 12:01 PM", collectionWeek="Week A", collectionDay="2"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            
            alert = ScheduledAlerts.query.first()
            self.assertEqual(alert.options, "00345")
            self.assertEqual(alert.type, "text")
            self.assertEqual(alert.collection_weeks, "Week A")
            self.assertEqual(alert.collection_days, "2")
            self.assertEqual(alert.datetime, datetime(2016, 1, 1, 12, 1))


    @mock.patch('app.db')
    def test_schedule_call_alert(self, db_mock):
        db_mock.return_value = self.db
        with self.app as c:
            result = c.post('/broadcast/', data=dict(opt1=0, opt2=0, opt3=3, opt4=4, opt5=5,
                        alert_type="call", callAlert="Testing a call alert", scheduledDate="01/01/2016 12:02 PM", collectionWeek="Week B", collectionDay="3"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            self.assertIsNotNone(result.data)
            
            alert = ScheduledAlerts.query.first()
            self.assertEqual(alert.options, "00345")
            self.assertEqual(alert.type, "call")
            self.assertEqual(alert.collection_weeks, "Week B")
            self.assertEqual(alert.collection_days, "3")
            self.assertEqual(alert.datetime, datetime(2016, 1, 1, 12, 2))


    @mock.patch('app.db')
    def test_immediate_text_alert(self, db_mock):
        db_mock.return_value = self.db
        sub = Subscription(address="123 Testing St", addressId = "123", optin="12345", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="2", schedule="Week A", notificationTime=14)
        self.db.session.add(sub)
        self.db.session.commit()

        with self.app as c:
            result = c.post('/broadcast/', data=dict(opt1=0, opt2=0, opt3=3, opt4=4, opt5=5,
                        alert_type="text", textAlert="Testing a text alert", scheduledDate="", collectionWeek="Week A", collectionDay="2"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            

    @mock.patch('app.db')
    def test_immediate_call_alert(self, db_mock):
        db_mock.return_value = self.db
        sub = Subscription(address="123 Testing St", addressId = "123", optin="12345", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="3", schedule="Week B", notificationTime=14)
        self.db.session.add(sub)
        self.db.session.commit()

        with self.app as c:
            result = c.post('/broadcast/', data=dict(opt1=0, opt2=0, opt3=3, opt4=4, opt5=5,
                        alert_type="call", callAlert="Testing a call alert", scheduledDate="", collectionWeek="Week B", collectionDay="3"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            


    @mock.patch("smtplib.SMTP")
    @mock.patch('reminders.db')
    @mock.patch('reminders.getNotificationDates')
    @mock.patch('reminders.holidayThisWeek')
    @mock.patch('reminders.eventsThisWeek')
    def test_send_regular_notifications_sunday(self, events_mock, holiday_mock, notification_dates_mock, db_mock, mock_smtplib):
        holiday_mock.return_value = {'isHoliday': False}
        notification_dates_mock.return_value = 1, 2, 14
        db_mock.return_value = self.db_reminders
        events_mock.return_value = []
        
        sub = reminders.Subscription(address="1 CARDEN ST", addressId = "5338", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", optin="12345", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="23456", schedule="Week Z", notificationTime=14)
        self.db_reminders.add(sub)
        reminders.sendNotifications()
        
        messageLog = self.db_reminders.query(reminders.MessageLog).first()
        self.assertEqual(messageLog.message_type, "Subscription")
        self.assertEqual(messageLog.sent, True)
        self.assertEqual(messageLog.method, "text")
        self.assertEqual(messageLog.phone_number, "5195555555")


    def test_reminders_getNotificationDates(self):
        with mock.patch('reminders.date') as mock_date:
            mock_date.today.return_value = date(2016, 10, 16)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            with mock.patch('reminders.datetime') as mock_datetime:
                mock_datetime.now.return_value = datetime(2016, 10, 16, 13, 0)
                mock_datetime.side_effect = lambda *args, **kw: date(*args, **kw)
        
                dayToday, dayTomorrow, currentHour = reminders.getNotificationDates()
    
                self.assertEqual(dayToday, 1)
                self.assertEqual(dayTomorrow, 2)
                self.assertEqual(currentHour, 13)


    @mock.patch("smtplib.SMTP")
    @mock.patch('reminders.db')
    @mock.patch('reminders.getNotificationDates')
    @mock.patch('reminders.generateSeasonalEvents')
    def test_send_regular_notifications(self, seasonal_events_mock, notification_dates_mock, db_mock, mock_smtplib):
        with mock.patch('reminders.date') as mock_date:
            mock_date.today.return_value = date(2016, 01, 02)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            notification_dates_mock.return_value = 1, 2, 14
            db_mock.return_value = self.db_reminders
            seasonal_events_mock.return_value = [["Test Event", "2016-01-02", "2016-01-02", "Testing an event"]]
            
            sub = reminders.Subscription(address="1 CARDEN ST", addressId = "5338", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", optin="12345", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="23456", schedule="Week Z", notificationTime=14)
            self.db_reminders.add(sub)
            reminders.sendNotifications()
            
            messageLog = self.db_reminders.query(reminders.MessageLog).first()
            self.assertEqual(messageLog.message_type, "Subscription")
            self.assertEqual(messageLog.sent, True)
            self.assertEqual(messageLog.method, "text")
            self.assertEqual(messageLog.phone_number, "5195555555")
        

    def test_no_address_unsubscribe(self):
        with self.app as c:
            result = c.post('/remove/', data=dict(address="", email="test@test.com", text="5195555555", call="5195555555"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "At this time your address is unavailable" in result.data


    def test_no_contact_unsubscribe(self):
        with self.app as c:
            result = c.post('/remove/', data=dict(address="1 CARDEN ST", email="", text="", call=""), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            assert "Please enter at least one method of contact" in result.data


    @mock.patch('app.db')
    @mock.patch("smtplib.SMTP")
    def test_unsubscribe(self, mock_smtp, db_mock):
        db_mock.return_value = self.db
        sub = Subscription(address="1 CARDEN ST", addressId = "123", optin="12345", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="2", schedule="Week A", notificationTime=14)
        self.db.session.add(sub)
        self.db.session.commit()

        with self.app as c:

            result = c.post('/remove/', data=dict(address="1 CARDEN ST", email="test@test.com", text="5195555555", call="5195555555"), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            
            sub = Subscription.query.first()
            self.assertEqual(sub.address, "1 CARDEN ST")
            self.assertEqual(sub.address_id, "123")
            self.assertEqual(sub.email_active, False)
            self.assertEqual(sub.email, "test@test.com")
            self.assertEqual(sub.opt_in, "12345")
            self.assertEqual(sub.call_phone_number, "5195555555")
            self.assertEqual(sub.call_number_active, False)
            self.assertEqual(sub.text_phone_number, "5195555555")
            self.assertEqual(sub.text_number_active, False)
            self.assertEqual(sub.collection_days, "2")
            self.assertEqual(sub.schedule, "Week A")
            self.assertEqual(sub.notification_time, 14)
            assert "successfully unsubscribed" in result.data
            mock_smtp.return_value.sendmail.assert_called_once


    @mock.patch('app.db')
    def test_add_remove_check_valid_address(self, db_mock):
        db_mock.return_value = self.db
        
        #Run this test 20 times to attempt 
        for x in range(1,20):
            sub = Subscription(address="1 CARDEN ST", addressId = "5338", optin="12345", email="test@test.com", emailActive=False, textPhoneNumber="5195555555", textNumberActive=False, callPhoneNumber="5195555555", callNumberActive=False, collectiondays="2", schedule="Week A", notificationTime=12, emailVerificationCode="E12345", textVerificationCode="T12345", callVerificationCode="C12345")
            self.db.session.add(sub)
            self.db.session.commit()
            
            self.db.session.delete(sub)
            self.db.session.commit()
            
            with self.app as c:
                result = c.post('/getInfo/', data=dict(
                        address="1 CARDEN ST"), follow_redirects=True)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(flask.session['address'], "1 CARDEN ST")
                self.assertEqual(flask.session['addressId'], "5338")
                self.assertEqual(flask.session['schedule'], "Week Z")
                self.assertIsNotNone(flask.session['collectionDay'])
                self.assertIsNotNone(flask.session['collectionDayNum'])
                self.assertIsNotNone(flask.session['pickupDates'])
                assert "Sign up for reminders" in result.data


    @mock.patch("smtplib.SMTP")
    @mock.patch('reminders.db')
    @mock.patch('reminders.getNotificationDates')
    def test_send_newyears_notifications_2017(self, notification_dates_mock, db_mock, mock_smtplib):
        with mock.patch('reminders.date') as mock_date:
            mock_date.today.return_value = date(2017, 12, 31)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            notification_dates_mock.return_value = 1, 2, 14
            db_mock.return_value = self.db_reminders
            
            sub = reminders.Subscription(address="1 CARDEN ST", addressId = "5338", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", optin="12345", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="23456", schedule="Week Z", notificationTime=14)
            self.db_reminders.add(sub)
            reminders.sendNotifications()
            
            messageLog = self.db_reminders.query(reminders.MessageLog).first()
            self.assertEqual(messageLog.message_type, "Subscription")
            self.assertEqual(messageLog.sent, True)
            self.assertEqual(messageLog.method, "text")
            self.assertEqual(messageLog.phone_number, "5195555555")
            self.assertEqual(reminders.holidayThisWeek(), {'isHoliday': True, 'dayNum': 2})
            

    @mock.patch("smtplib.SMTP")
    @mock.patch('reminders.db')
    @mock.patch('reminders.getNotificationDates')
    def test_send_newyears_notifications_2018(self, notification_dates_mock, db_mock, mock_smtplib):
        with mock.patch('reminders.date') as mock_date:
            mock_date.today.return_value = date(2018, 12, 31)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            notification_dates_mock.return_value = 1, 2, 14
            db_mock.return_value = self.db_reminders
            
            sub = reminders.Subscription(address="1 CARDEN ST", addressId = "5338", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", optin="12345", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="23456", schedule="Week Z", notificationTime=14)
            self.db_reminders.add(sub)
            reminders.sendNotifications()
            
            messageLog = self.db_reminders.query(reminders.MessageLog).first()
            self.assertEqual(messageLog.message_type, "Subscription")
            self.assertEqual(messageLog.sent, True)
            self.assertEqual(messageLog.method, "text")
            self.assertEqual(messageLog.phone_number, "5195555555")
            self.assertEqual(reminders.holidayThisWeek(), {'isHoliday': True, 'dayNum': 3})


    @mock.patch("smtplib.SMTP")
    @mock.patch('reminders.db')
    @mock.patch('reminders.getNotificationDates')
    def test_send_newyears_notifications_2019(self, notification_dates_mock, db_mock, mock_smtplib):
        with mock.patch('reminders.date') as mock_date:
            mock_date.today.return_value = date(2019, 12, 31)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            notification_dates_mock.return_value = 1, 2, 14
            db_mock.return_value = self.db_reminders
            
            sub = reminders.Subscription(address="1 CARDEN ST", addressId = "5338", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", optin="12345", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="23456", schedule="Week Z", notificationTime=14)
            self.db_reminders.add(sub)
            reminders.sendNotifications()
            
            messageLog = self.db_reminders.query(reminders.MessageLog).first()
            self.assertEqual(messageLog.message_type, "Subscription")
            self.assertEqual(messageLog.sent, True)
            self.assertEqual(messageLog.method, "text")
            self.assertEqual(messageLog.phone_number, "5195555555")
            self.assertEqual(reminders.holidayThisWeek(), {'isHoliday': True, 'dayNum': 4})


    @mock.patch("smtplib.SMTP")
    @mock.patch('reminders.db')
    @mock.patch('reminders.getNotificationDates')
    def test_send_newyears_notifications_2020(self, notification_dates_mock, db_mock, mock_smtplib):
        with mock.patch('reminders.date') as mock_date:
            mock_date.today.return_value = date(2020, 12, 31)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            notification_dates_mock.return_value = 1, 2, 14
            db_mock.return_value = self.db_reminders
            
            sub = reminders.Subscription(address="1 CARDEN ST", addressId = "5338", email="test@test.com", emailActive=True, textPhoneNumber="5195555555", optin="12345", textNumberActive=True, callPhoneNumber="5195555555", callNumberActive=True, collectiondays="23456", schedule="Week Z", notificationTime=14)
            self.db_reminders.add(sub)
            reminders.sendNotifications()
            
            messageLog = self.db_reminders.query(reminders.MessageLog).first()
            self.assertEqual(messageLog.message_type, "Subscription")
            self.assertEqual(messageLog.sent, True)
            self.assertEqual(messageLog.method, "text")
            self.assertEqual(messageLog.phone_number, "5195555555")
            self.assertEqual(reminders.holidayThisWeek(), {'isHoliday': True, 'dayNum': 6})
            

# runs the unit tests in the module
if __name__ == '__main__':
    try:
        unittest.main()
    except:
        pass