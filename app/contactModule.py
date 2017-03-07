import twilio.rest
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import email.utils
import time
import os

import config


class TwilioContact():
       
    def __init__(self, session, writeMessageLog, Logger):
        ##### TWILIO - USED FOR CALLS AND TEXTS #####
        self.client = twilio.rest.TwilioRestClient(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        self.writeMessageLog = writeMessageLog
        self.session = session
        self.logger = Logger

    
    def sendTwilioSubscriptionCall(self, toNumber, msg, options, weeks, days):
        return self.twilioContact(toNumber, "call", msg, "Subscription", options, weeks, days)
    
    def sendTwilioSubscriptionText(self, toNumber, msg, options, weeks, days):
        return self.twilioContact(toNumber, "text", msg, "Subscription", options, weeks, days)
    
    def sendTwilioAlertCall(self, toNumber, msg, options, weeks, days):
        return self.twilioContact(toNumber, "call", msg, "Alert", options, weeks, days)
    
    def sendTwilioAlertText(self, toNumber, msg, options, weeks, days):
        return self.twilioContact(toNumber, "text", msg, "Alert", options, weeks, days)
    
    def sendTwilioEventCall(self, toNumber, msg, options=None):
        return self.twilioContact(toNumber, "call", msg, "Event", options)
    
    def sendTwilioEventText(self, toNumber, msg, options=None):
        return self.twilioContact(toNumber, "text", msg, "Event", options)
    
    def sendTwilioSignUpCall(self, toNumber, msg, options, weeks, days):
        return self.twilioContact(toNumber, "call", msg, "SignUp", options, weeks, days)
    
    def sendTwilioSignUpText(self, toNumber, msg, options, weeks, days):
        return self.twilioContact(toNumber, "text", msg, "SignUp", options, weeks, days)

    def sendTwilioVerificationCall(self, toNumber, msg, options, weeks, days):
        return self.twilioContact(toNumber, "call", msg, "Verification", options, weeks, days)
    
    def sendTwilioVerificationText(self, toNumber, msg, options, weeks, days):
        return self.twilioContact(toNumber, "text", msg, "Verification", options, weeks, days)

    def sendTwilioUnsubscribeCall(self, toNumber, msg):
        return self.twilioContact(toNumber, "call", msg, "Unsubscribe")
    
    def sendTwilioUnsubscribeText(self, toNumber, msg):
        return self.twilioContact(toNumber, "text", msg, "Unsubscribe")
    
  
    def twilioContact(self, toNumber, method, msg, msgType, options=None, weeks=None, days=None):
        try:
            if method == 'call':
                #Duplicate msg to have Twilio repeat it just to ensure it gets picked up on VM.
                msg = msg + ". . . . . . . . ." + msg + ". . . . . . . . ." + msg
                callUrl = 'http://twimlets.com/message?IfMachine=Continue&Message%5B0%5D='+(msg.replace(chr(13)+chr(10),'%0A').replace(chr(32),'%20')) + '&'
                message = self.client.calls.create(to=toNumber,  # Any phone number
                                   from_=config.TWILIO_FROM_NUMBER, # Must be a valid Twilio number
                                   url=callUrl)
                self.logger.info("Successfully completed call: %s" % message.sid)
            else:
                message = self.client.messages.create(body=msg,
                        to=toNumber,    # Replace with your phone number
                        from_=config.TWILIO_FROM_NUMBER)
    
                self.logger.info("Successfully sent text: %s" % message.sid)
            
            # Log successful msg send
            self.writeMessageLog(self.session, msgType, method, phone_number=toNumber, options=options, collection_weeks=weeks, collection_days=days, sent=True, notes="Successfully sent: %s" % message.sid)
            #return True
        
        except twilio.TwilioRestException as e:
            # Log unsuccessful send
            self.writeMessageLog(self.session, msgType, method, phone_number=toNumber, options=options, collection_weeks=weeks, collection_days=days, sent=False, notes="Failed to send: %s" % e)
            #self.logger.critical("Twilio Exception: %s" % e)
            self.logger.critical("Traceback: %s" % traceback.format_exc())
            raise
    ######### END OF TWILIO ###################


class EmailContact():
    
    def __init__(self, session, writeMessageLog, Logger):
        self.writeMessageLog = writeMessageLog
        self.session = session
        self.logger = Logger
    
    def sendSubscriptionEmail(self, to_addr, subject, msg, options, weeks, days):
        return self.sendEmail(to_addr, subject, msg, "Subscription", options, weeks, days)
        
    def sendEventEmail(self, to_addr, subject, msg, options):
        return self.sendEmail(to_addr, subject, msg, "Event", options)
        
    def sendAlertEmail(self, to_addr, subject, msg, options, weeks, days):
        return self.sendEmail(to_addr, subject, msg, "Alert", options, weeks, days)
        
    def sendSignUpEmail(self, to_addr, subject, msg, options, weeks, days):
        return self.sendEmail(to_addr, subject, msg, "SignUp", options, weeks, days)
    
    def sendVerificationEmail(self, to_addr, subject, msg, options, weeks, days):
        return self.sendEmail(to_addr, subject, msg, "Verification", options, weeks, days)
        
    def sendUnsubscribeEmail(self, to_addr, subject, msg):
        return self.sendEmail(to_addr, subject, msg, "Unsubscribe")
    
    ######### EMAIL FUNCTION USED TO SEND EMAILS #############
    def sendEmail(self, toAddress, subject, message, msgType, options=None, weeks=None, days=None):
        try:

            fromAddress = config.MAIL_FROM
            smtpServer = config.MAIL_SERVER
    
            msg = MIMEMultipart('related')
            msg['Subject'] = subject
            msg['To'] = toAddress
            msg['Message-ID'] = email.utils.make_msgid()
            msg['Date'] = email.utils.formatdate(time.time(), localtime=True)
            msg['From'] = fromAddress
            
            part = MIMEText(message, 'html')
            msg.attach(part)
            
            #Read in COG logo
            with open(config.EMAIL_LOGO, 'rb') as file:
                msgImage = MIMEImage(file.read(), name=os.path.basename(config.EMAIL_LOGO))
                msg.attach(msgImage)          
            msgImage.add_header('Content-ID', '<COG_LOGO>')
            
            #Read in COG Waste logo
            with open(config.EMAIL_WASTE_LOGO, 'rb') as file:
                msgImage = MIMEImage(file.read(), name=os.path.basename(config.EMAIL_WASTE_LOGO))
                msg.attach(msgImage)          
            msgImage.add_header('Content-ID', '<WASTE_LOGO>')
            
            server = smtplib.SMTP(smtpServer)
            
            if config.MAIL_USERNAME or config.MAIL_PASSWORD:
                server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
    
            server.sendmail(fromAddress, toAddress, msg.as_string())
            
            server.quit()
            self.logger.info("Email successfully sent: %s" % toAddress)
            self.writeMessageLog(self.session, msgType, "email", email=toAddress, options=options, collection_weeks=weeks, collection_days=days, sent=True, notes="Successfully sent")
            #return True
        
        except Exception, e:
            self.writeMessageLog(self.session, msgType, "email", email=toAddress, options=options, collection_weeks=weeks, collection_days=days, sent=False, notes="Failed to send")
            #self.logger.critical("Exception: %s" % e)
            self.logger.critical("Traceback: %s" % traceback.format_exc())
            raise
    
    ##################### END OF EMAIL #####################
