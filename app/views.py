from flask import render_template, redirect, request, \
    url_for, flash, make_response, session
from flask_security import login_required
    
from parsingModule import getSchedule, getIDInfo, generateSeasonalEvents, \
    generateStatHolidays

from forms import SignUpForm

from app import app, os, addressDictionary, getSetting, validateForm, \
    validateOpts, recaptcha, Subscription, write_log, removeDuplicates, myTwilioContact, myEmailContact, \
    ScheduledAlerts, date, militaryToStandard, datetime, getPickupDates, current_user, logger
import config

from UniversalAnalytics import Tracker

import traceback
import random
import uuid

mySubscription = Subscription()

if config.isProduction:
    tracker_primary = Tracker.create(config.ANALYTICS_KEY_PRIMARY)
    tracker_secondary = Tracker.create(config.ANALYTICS_KEY_SECONDARY)


def clearSession():
    """ Clear session variables as needed """
    logger.info("Clear session called")
    if session.get('address', None): session.pop('address')
    if session.get('emailAddress', None): session.pop('emailAddress')
    if session.get('textPhoneNumber', None): session.pop('textPhoneNumber')
    if session.get('callPhoneNumber', None): session.pop('callPhoneNumber')
    if session.get('options', None): session.pop('options')
    if session.get('scheduledTime', None): session.pop('scheduledTime')
    if session.get('uid', None): session.pop('uid')


@app.before_request
def make_session_permanent():
    """ Set session.permanent to allow us to define a timeout period for the session """
    session.permanent = True

@app.context_processor
def inject_details():
    """ Inject variables on each web request """
    
    return dict(emailAddress = session.get('emailAddress', ""),
                textPhoneNumber = session.get('textPhoneNumber', ""),
                callPhoneNumber = session.get('callPhoneNumber', ""), 
                address=session.get('address', ""),
                addressId=session.get('addressId', None),
                collectionDay=session.get('collectionDay', None), 
                schedule=session.get('schedule', None),
                nextDate=session.get('nextPickupDate', None), 
                nextCarts=session.get('nextCarts', None))
    

@app.after_request
def apply_caching(response):
    """
    Set security on domains that are allowed to use site in an iframe 

    """

    if os.environ.get('FRAME_ALLOW_URL') is None:
        allowUrl = getSetting("Security", "frameAllowURL")        
    else:
        allowUrl = os.environ.get('FRAME_ALLOW_URL')
        
    response.headers["X-Frame-Options"] = "ALLOW-FROM %s" % allowUrl
    response.headers["Content-Security-Policy"] = "frame-ancestors %s" % allowUrl
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
 
 
@app.route("/")
def home():
    clearSession()
    addresses = []
    logger.debug("requested home")
    
    if config.isProduction:
        tracker_primary.send('pageview', path = "/", title = "Home Page") 
        tracker_secondary.send('pageview', path = "/", title = "Home Page")

    for i in addressDictionary:
        addresses.append(i)
    return render_template("index.html", lst = addresses)
 
 
@app.route('/getInfo/', methods=['GET', 'POST'])
def getInfo():
    
    try:
        
        session['uid'] = uuid.uuid4()
        logger.debug("%s - requested getInfo" % session.get('uid', None))
        
        if config.isProduction:
            tracker_primary.send('pageview', path = "/getInfo", title = "Collection Info")
            tracker_secondary.send('pageview', path = "/getInfo", title = "Collection Info")

        todayCarts = None
        
        if request.method == 'POST':
            address = request.form['address'].upper() # get the address of the user
            if not address or address not in addressDictionary:
                flash(getSetting("Signup", "invalidaddress"))
                return redirect(url_for('home')) # redirect back to home page
            
            logger.debug("%s - Address requested: %s" % (session.get('uid', None), address))
            
            session['address'] = address
            
            addressId = addressDictionary[address] # wherever the address was in the address list, the id will have the same position in ids
            addressInfo = getIDInfo(str(addressId)) # get the information
            schedule = addressInfo['schedule']

            #IF schedule is not found eg. ZZ
            if not schedule:
                flash(getSetting("Signup", "invalidaddress"))
                return redirect(url_for('home')) # redirect back to home page
 
            #collectionInfo = getIDInfo(str(id))
            session['collectionDayNum'] = addressInfo['originalDays']
            pickupDates = getPickupDates()

            if schedule == "Week Z":
                collectionDay = ["Mon","-","Fri"]
                session['pickupDates'] = ""
            else:
                collectionDay = addressInfo['newDays']
                session['pickupDates'] = pickupDates
                
            session['addressId'] = addressId                 
            session['schedule'] = schedule           
            session['collectionDay'] = collectionDay

            yearSched = getSchedule(schedule, pickupDates)
            session['yearSched'] = yearSched
            
            for y in pickupDates: # for every pickup date
                thisDate = datetime.strptime(y,'%Y-%m-%d').date() # look at it as a real date
                
                ## Check if today is a pickup date, get cart information
                if thisDate == date.today():
                    todayCarts  = yearSched[1][pickupDates.index(y)]
                
                ## Get next pickup details
                if thisDate > date.today(): #if this pickup date comes after today
                    session['nextPickupDate'] = thisDate.strftime("%A, %B %d, %Y") #we have when our next pickup will be
                    session['nextCarts'] = yearSched[1][pickupDates.index(y)]
                    break; #stop processing
 
        return render_template("signup.html", todayCarts = todayCarts)
 
    except Exception as e:
        logger.critical("Traceback: %s" % traceback.format_exc())
        flash(getSetting("ErrorMessage", "general"))
        return redirect(url_for('home'))
  
    
@app.route('/signup/', methods=['GET','POST'])
def signup():
    
    emailAddress = None
    textPhoneNumber = None
    callPhoneNumber = None
  
    try:
        
        logger.debug("%s - requested signup" % session.get('uid', None))
        
        if config.isProduction:
            tracker_primary.send('pageview', path = "/signup", title = "Start Reminders Signup")
            tracker_secondary.send('pageview', path = "/signup", title = "Start Reminders Signup")
        
        #Check if we still have the address stored in session
        #If not redirect back to home page to start again
        if not session.get('address', None):
            flash(getSetting("ErrorMessage", "sessionExpired"))
            logger.info("Session expired redirecting back home")
            return redirect(url_for('home')) # redirect back to home page
 
        if request.method == 'POST':

            if recaptcha.verify():
                if request.form['email']:  
                    form = SignUpForm(request.form)
                    if form.validate():
                        emailAddress = request.form['email']
                        session['emailAddress'] = emailAddress
                        #logger.debug("%s - email address signup: %s" % (session.get('uid', None), emailAddress))
                    else:
                        if session.get('emailAddress', None): session.pop('emailAddress')
                        flash("Please enter a valid email address")
                        return redirect(url_for('getInfo'))
                else:
                    session['emailAddress'] = ""                    
                if request.form['text']:
                    textPhoneNumber = request.form['text']
                    session['textPhoneNumber'] = textPhoneNumber
                    #logger.debug("%s - text number signup: %s" % (session.get('uid', None), textPhoneNumber))
                else:
                    session['textPhoneNumber'] = ""        
                if request.form['call']:
                    callPhoneNumber = request.form['call']
                    session['callPhoneNumber'] = callPhoneNumber
                    #logger.debug("%s - call number signup: %s" % (session.get('uid', None), callPhoneNumber))
                else:
                    session['callPhoneNumber'] = ""        
        
                isBad = validateForm(emailAddress, textPhoneNumber, callPhoneNumber) # make sure everything makes sense
                if isBad:
                    for m in isBad:
                        flash(m) # otherwise output all the errors
                    return redirect(url_for('getInfo')) # redirect back to home page
            else:
                flash(getSetting("ErrorMessage", "captcha"))
                return redirect(url_for('getInfo')) # redirect back to home page
            
        return render_template("notifications.html")
 
    except Exception as e:
        logger.critical("Traceback: %s" % traceback.format_exc())
        flash(getSetting("ErrorMessage", "general"))
        return redirect(url_for('getInfo'))
 
 
def generateValidationCode():
    return str(random.randrange(10000,99999))
 
 
@app.route('/confirmation/', methods=['GET','POST'])
def confirmation():
    try:
        
        logger.debug("%s - requested confirmation" % session.get('uid', None))
        
        if config.isProduction:
            tracker_primary.send('pageview', path = "/confirmation", title = "Select Reminder Options")
            tracker_secondary.send('pageview', path = "/confirmation", title = "Select Reminder Options")

        #Check if we still have the address stored in session
        #If not redirect back to home page to start again
        if not session.get('address', None):
            flash(getSetting("ErrorMessage", "sessionExpired"))
            logger.info("Session expired redirecting back home")
            return redirect(url_for('home')) # redirect back to home page
        
        if request.method == 'POST':
               
            emailAddress = session.get('emailAddress', None)
            textPhoneNumber = session.get('textPhoneNumber', None)
            callPhoneNumber = session.get('callPhoneNumber', None)
            scheduledTime = request.form['time']
            session['scheduledTime'] = scheduledTime
            logger.debug("%s - scheduled time signup: %s" % (session.get('uid', None), scheduledTime))
            
            optString=""
            optInBoxes = ['optin1','optin2','optin3','optin4','optin5']
            for o in optInBoxes:
                try:
                    result = request.form.get(o)
                    optString+=result
                except TypeError:
                    optString+='0'
 
            invalidOpts = validateOpts(optString)
            if invalidOpts:
                flash(invalidOpts[0])
                return redirect(url_for('signup'))
            
            session['options'] = optString
            logger.debug("%s - options signup: %s" % (session.get('uid', None), optString))
            
            emailVerificationCode = None
            callVerificationCode = None
            textVerificationCode = None
                                 
            # SEND OUT THE CONFIRMATIONS FOR EACH METHOD ENTERED
            if emailAddress:
                emailVerificationCode = "1" + generateValidationCode()
                msg = getSetting("VerificationMessage", "email").format(emailVerificationCode)
                logger.debug("%s - email verification code: %s" % (session.get('uid', None), emailVerificationCode))
                myEmailContact.sendSignUpEmail(emailAddress, 'Guelph Waste Notification Verification', msg, options=optString, weeks=session.get('schedule', None), days=';'.join(session.get('collectionDayNum', None)))
            if textPhoneNumber:
                textVerificationCode = "2" + generateValidationCode()
                msg = getSetting("VerificationMessage", "text").format(textVerificationCode)
                logger.debug("%s - text verification code: %s" % (session.get('uid', None), textVerificationCode))
                myTwilioContact.sendTwilioSignUpText(textPhoneNumber, msg, options=optString, weeks=session.get('schedule', None), days=';'.join(session.get('collectionDayNum', None)))
            if callPhoneNumber:
                callVerificationCode = "3" + generateValidationCode()
                callPausedCode = ',,,,,,,,,,,,,,,,,,,,,' + ',,,,,,,,,,,,,,,,,,,,,'.join(callVerificationCode[i:i+1] for i in range(0, len(callVerificationCode), 1))
                msg = getSetting("VerificationMessage", "call").format(callPausedCode, callPausedCode)
                logger.debug("%s - call verification code: %s" % (session.get('uid', None), callVerificationCode))
                myTwilioContact.sendTwilioSignUpCall(callPhoneNumber, msg, options=optString, weeks=session.get('schedule', None), days=';'.join(session.get('collectionDayNum', None)))

            mySubscription.addSubscription(session.get('address', None), session.get('addressId', None), emailAddress, optString, callPhoneNumber, textPhoneNumber, session.get('collectionDayNum', None), session.get('schedule', None), int(scheduledTime), emailVerificationCode, textVerificationCode, callVerificationCode) # add them to the DB

            session['emailVerificationCode'] = emailVerificationCode
            session['textVerificationCode'] = textVerificationCode
            session['callVerificationCode'] = callVerificationCode
             
        response = make_response(render_template("confirmation.html"))      
        return response
 
    except Exception as e:
        logger.critical("Traceback: %s" % traceback.format_exc())
        flash(getSetting("ErrorMessage", "general"))
        return redirect(url_for('signup'))
 
 
@app.route('/verify/', methods=['GET','POST'])
def verify():
    
    try:
        
        logger.debug("%s - requested verify" % session.get('uid', None))
        
        if config.isProduction:
            tracker_primary.send('pageview', path = "/verify", title = "Verify Signup")
            tracker_secondary.send('pageview', path = "/verify", title = "Verify Signup")
        
        #Check if we still have the address stored in session
        #If not redirect back to home page to start again
        if not session.get('address', None):
            flash(getSetting("ErrorMessage", "sessionExpired"))
            logger.info("Session expired redirecting back home")
            return redirect(url_for('home')) # redirect back to home page
        
        if request.method == 'POST':
           
            #address = session.get('address', None)
            emailAddress = session.get('emailAddress', None)
            if not emailAddress:
                emailAddress = None
            textPhoneNumber = session.get('textPhoneNumber', None)
            if not textPhoneNumber:
                textPhoneNumber = None
            callPhoneNumber = session.get('callPhoneNumber', None)
            if not callPhoneNumber:
                callPhoneNumber = None
            scheduledTime = session.get('scheduledTime', None)
            emailVerificationCode = session.get('emailVerificationCode', None)
            textVerificationCode = session.get('textVerificationCode', None)
            callVerificationCode = session.get('callVerificationCode', None)            
            
            emailActive = False
            textActive = False
            callActive = False
            newTime = militaryToStandard(scheduledTime)
            error = False
          
            if emailAddress:
                inputEmailCode = request.form['emailCode']
                
                if inputEmailCode:
                    if inputEmailCode.strip().lower() == emailVerificationCode.lower():
                        emailActive = True
                    else:
                        flash(getSetting("ErrorMessage", "invalidEmailVerifaction"))
                        error = True
                else:
                    flash(getSetting("ErrorMessage", "emptyEmailVerification"))
                    error = True
    
            if textPhoneNumber:
                inputTextCode = request.form['textCode']
                
                if inputTextCode:
                    if inputTextCode.strip().lower() == textVerificationCode.lower():
                        textActive = True
                    else:
                        flash(getSetting("ErrorMessage", "invalidTextVerifaction"))
                        error = True
                else:
                    flash(getSetting("ErrorMessage", "emptyTextVerification"))
                    error = True
    
            if callPhoneNumber:
                inputCallCode = request.form['callCode']
                
                if inputCallCode:
                    if inputCallCode.strip().lower() == callVerificationCode.lower():
                        callActive = True
                    else:
                        flash(getSetting("ErrorMessage", "invalidCallVerifaction"))
                        error = True
                else:
                    flash(getSetting("ErrorMessage", "emptyCallVerification"))
                    error = True
 
            # If an error has been encountered then redirect back to same page with error msgs
            if error:
                return redirect(url_for('confirmation'))
            
            # If no error then send success messages
            if emailActive:
                msg = getSetting("SuccessRegisteredMessage", "email").format(newTime)
                myEmailContact.sendVerificationEmail(emailAddress, 'Successful Registration', msg, options=session.get('options', None), weeks=session.get('schedule', None), days=';'.join(session.get('collectionDayNum', None)))
                
            if textActive:
                msg = getSetting("SuccessRegisteredMessage", "text").format(newTime)
                myTwilioContact.sendTwilioVerificationText(textPhoneNumber, msg, options=session.get('options', None), weeks=session.get('schedule', None), days=';'.join(session.get('collectionDayNum', None)))
           
            mySubscription.updateActivateSub(emailAddress, emailActive, emailVerificationCode, textPhoneNumber, textActive, textVerificationCode, callPhoneNumber, callActive, callVerificationCode)
        
        if config.isProduction:
            tracker_primary.send('event', 'Subscription', 'Successfully Signed Up')
            tracker_secondary.send('event', 'Subscription', 'Successfully Signed Up')

        response = make_response(render_template("done.html"))
        session.clear()
        return response
     
    except Exception as e:
        logger.critical("Traceback: %s" % traceback.format_exc())
        flash(getSetting("ErrorMessage", "verification"))
        return redirect(url_for('confirmation'))
 
 
@app.route('/calendar/', methods=['GET'])
def calendar():

    logger.debug("%s - requested calendar" % session.get('uid', None))
    
    if config.isProduction:
        tracker_primary.send('pageview', path = "/calendar", title = "Calendar")
        tracker_secondary.send('pageview', path = "/calendar", title = "Calendar")
    
    #Check if we still have the address stored in session
    #If not redirect back to home page to start again
    if not session.get('address', None):
        flash(getSetting("ErrorMessage", "sessionExpired"))
        logger.info("Session expired redirecting back home")
        return redirect(url_for('home')) # redirect back to home page
    
    statDates = generateStatHolidays() # list of stat dates for calendar entry
    specialEvents = generateSeasonalEvents() # special events for cal entry      

    pickupDates = session.get('pickupDates', None)      
    schedule = session.get('schedule', None)
    yearSched = session.get('yearSched', None)
    
    if schedule in ('Week A', 'Week B'):
        pdfLink = getSetting("Admin", schedule.replace(" ", "").lower() + "_PDFLink")
    else:
        pdfLink = None
        
    statHolidayDesc = getSetting("CalendarCartDetails", "statHoliday")
    greenCartDesc = getSetting("CalendarCartDetails", "greenCart")
    blueCartDesc = getSetting("CalendarCartDetails", "blueCart")
    greyCartDesc = getSetting("CalendarCartDetails", "greyCart")
    
    return render_template("calendar.html", pdfLink=pdfLink, pickupDays=pickupDates, schedList=yearSched, statHolidayDesc=statHolidayDesc, greenCartDesc=greenCartDesc, blueCartDesc=blueCartDesc, greyCartDesc=greyCartDesc, statDates=statDates, specialEvents=specialEvents) 
  
 
@app.route('/download/', methods=['GET', 'POST'])
def download():
 
    try:
        logger.debug("%s - requested download ics" % session.get('uid', None))
        
        if config.isProduction:
            tracker_primary.send('pageview', path = "/download", title = "Download Calendar")
            tracker_secondary.send('pageview', path = "/download", title = "Download Calendar")
        
        #Check if we still have the address stored in session
        #If not redirect back to home page to start again
        if not session.get('address', None):
            flash(getSetting("ErrorMessage", "sessionExpired"))
            logger.info("Session expired redirecting back home")
            return redirect(url_for('home')) # redirect back to home page
        
        icsText = "BEGIN:VCALENDAR\nVERSION:2.0\n"
        
        statDates = generateStatHolidays() # list of stat dates for calendar entry
        specialEvents = generateSeasonalEvents() # special events for cal entry   
        pickupDates = session.get('pickupDates', None)
        listOfColors = session.get('yearSched', None)
        
        if listOfColors is None:
            return redirect(url_for('getInfo'))
        
        for i in range(0, len(pickupDates)):
            date = pickupDates[i].replace("-","")
            toAppend = "BEGIN:VEVENT\nDTSTART;VALUE=DATE:%s\nDTEND;VALUE=DATE:%s\nSUMMARY:%s Cart\nEND:VEVENT\n" % (date + "T063000", date + "T063000", listOfColors[1][i][0])
            icsText += toAppend
            toAppend = "BEGIN:VEVENT\nDTSTART;VALUE=DATE:%s\nDTEND;VALUE=DATE:%s\nSUMMARY:GREEN Cart\nEND:VEVENT\n" % (date + "T063000", date + "T063000")
            icsText += toAppend
        
        for d in statDates:
            date = d.replace("-","")
            toAppend = "BEGIN:VEVENT\nDTSTART;VALUE=DATE:%s\nDTEND;VALUE=DATE:%s\nSUMMARY:Statutory Holiday\nEND:VEVENT\n" % (date, date)
            icsText += toAppend
        
        for e in specialEvents:
            sDate = e[1].replace("-","")
            eDate = e[2].replace("-","")
            toAppend = "BEGIN:VEVENT\nDTSTART;VALUE=DATE:%s\nDTEND;VALUE=DATE:%s\nSUMMARY:%s\nDESCRIPTION:%s\nEND:VEVENT\n" % (sDate,eDate,e[0],e[3])
            icsText += toAppend
        
        icsText += "END:VCALENDAR"
        
        response = make_response(icsText)
        # This is the key: Set the right header for the response
        # to be downloaded, instead of just printed on the browser
        response.headers["Content-Disposition"] = "attachment; filename=%s.ics" % (getSetting('Calendar','filename'))
        response.headers["Content-Type"] = "text/calendar"
        return response
 
    except Exception as e:
        logger.critical("Traceback: %s" % traceback.format_exc())
        flash(getSetting("ErrorMessage", "general"))
        return redirect(url_for('calendar'))
 
 
@login_required
@app.route('/broadcast/', methods=['POST'])
def schedule_alert():
   
    logger.debug("requested broadcast alert")
    
    if config.isProduction:
        tracker_primary.send('pageview', path = "/broadcast", title = "Send or Schedule Alert")
        tracker_secondary.send('pageview', path = "/broadcast", title = "Send or Schedule Alert")
    
    if request.method == 'POST':
        
        alert_type = request.form['alert_type']          
        collectionWeeks = request.form.getlist('collectionWeek')
        collectionDays = request.form.getlist('collectionDay')
             
        options=""
        optInBoxes = ['opt1','opt2','opt3','opt4','opt5']
        for o in optInBoxes:
            try:
                result = request.form.get(o)
                options+=result
            except TypeError:
                options+="0"
 
        invalidOpts = validateOpts(options)
        if invalidOpts:
            flash("Please select at least one user type.")
            return redirect('admin/alerts')


        optionList = list(options.replace("0", ""))             
        message = ""
              
        if alert_type == 'text':
            
            if not request.form['textAlert']:
                flash("Please enter a text message")
                return redirect('admin/alerts')
            else:
                message = request.form['textAlert']
                     
        elif alert_type == 'call':
    
            if not request.form['callAlert']:
                flash("Please enter a call message")
                return redirect('admin/alerts')
            else:
                message = request.form['callAlert']
             
        elif alert_type == 'email':
            emails = mySubscription.findActiveEmailSubscriptions(optionList, collectionWeeks, collectionDays)
            emails = removeDuplicates(emails)
            respStr = ""
            try:
                for email in emails:
                    respStr += email.email + ";"
            except:
                pass
            
            if emails:
                response = make_response(respStr)
                response.headers["Content-Disposition"] = "attachment; filename=%s.txt" % (getSetting('Admin','emailFilename'))
                #flash("Successfully downloaded emails.txt")
                return response
            else:
                flash("No active emails found for the given criteria")
                return redirect('admin/alerts')
        
        else:
            flash("Invalid Alert Type")
            return redirect('admin/alerts')
 
 
        #Get Current user
        if current_user.is_authenticated:
            user = current_user.user_name
        else:
            user = "None"
            
        
        if not request.form['scheduledDate'] and alert_type != 'email':
            #Send alert immediately if we don't have a scheduled datetime
            
            if alert_type == 'text':
                numbers = mySubscription.findActiveTextSubscriptions(optionList, collectionWeeks, collectionDays)
            elif alert_type == 'call':
                numbers = mySubscription.findActiveCallSubscriptions(optionList, collectionWeeks, collectionDays)
            
            alerts_sent = 0
            for number in numbers:
                if alert_type == 'text':
                    myTwilioContact.sendTwilioAlertText(number.text_phone_number, message, options=options, weeks=';'.join(collectionWeeks), days=';'.join(collectionDays))
                    alerts_sent +=1
                elif alert_type == 'call':
                    myTwilioContact.sendTwilioAlertCall(number.call_phone_number, message, options=options, weeks=';'.join(collectionWeeks), days=';'.join(collectionDays))
                    alerts_sent +=1
                
            write_log(user, "Sent immediate alert to %d users: %s" % (alerts_sent, message))
            logger.info("Sent scheduled alert to %d users: %s" % (alerts_sent, message))
            flash("Alert successfully sent to %d Users" % alerts_sent)
            
        elif request.form['scheduledDate'] and alert_type != 'email':
            # Write Scheduled Alert to DB
            
            scheduledAlert = ScheduledAlerts()
            scheduledDate = datetime.strptime(request.form['scheduledDate'], '%d/%m/%Y %I:%M %p')
            scheduledAlert.addAlert(user, options, ';'.join(collectionWeeks), ';'.join(collectionDays), scheduledDate, alert_type, message)
        
            #Write log          
            write_log(user, "Scheduled new alert: %s" % message)
            flash("Alert successfully scheduled")
            
        return redirect('admin/alerts')
        
 
@app.route("/unsubscribe/", methods=['GET'])
def unsubscribe():
    
    clearSession()
    session['uid'] = uuid.uuid4()
    
    logger.debug("%s - requested unsubscribe" % session.get('uid', None))
    
    if config.isProduction:
        tracker_primary.send('pageview', path = "/unsubscribe", title = "Unsubscribe")
        tracker_secondary.send('pageview', path = "/unsubscribe", title = "Unsubscribe")

    addresses = []
    for i in addressDictionary:
        addresses.append(i)
    
    return render_template("unsubscribe.html", lst = addresses)
 
 
@app.route("/remove/", methods=['GET', 'POST'])
def unsubscribeRemoved():
   
    try:
        logger.debug("%s - requested remove" % session.get('uid', None))

        if config.isProduction:
            tracker_primary.send('pageview', path = "/remove", title = "Unsubscribed from Reminders")
            tracker_secondary.send('pageview', path = "/remove", title = "Unsubscribed from Reminders")

        removeEmailAddress = None
        removeTextPhoneNumber = None
        removeCallPhoneNumber = None
                       
        if request.method == 'GET':
            return redirect('unsubscribe')
            
        elif request.method == 'POST':
 
            address = request.form['address'].upper()
            if request.form['email']:        
                removeEmailAddress = request.form['email']
            if request.form['text']:
                removeTextPhoneNumber = request.form['text']
            if request.form['call']:
                removeCallPhoneNumber = request.form['call']
                       
            #Check if an address has been entered
            if not address or address not in addressDictionary:
                flash(getSetting("Signup", "invalidaddress"))
                return redirect(url_for('unsubscribe'))

            #Make sure at least one contact type has been entered
            if not removeEmailAddress and not removeTextPhoneNumber and not removeCallPhoneNumber:
                flash(getSetting("Signup", "noemailorphone"))
                return redirect(url_for('unsubscribe'))               
            
            if removeEmailAddress:        
                removed = mySubscription.unsubscribeEmail(address, removeEmailAddress)  
                if not removed:           
                    msg = getSetting("UnsubscribeMessage", "email").format(address)
                    myEmailContact.sendUnsubscribeEmail(removeEmailAddress, 'Unsubscribed', msg)
                else:
                    flash(removed)
                    return redirect(url_for('unsubscribe'))
    
            if removeTextPhoneNumber:
                removed = mySubscription.unsubscribeText(address, removeTextPhoneNumber)
                if not removed:
                    msg = getSetting("UnsubscribeMessage", "text").format(address)
                    myTwilioContact.sendTwilioUnsubscribeText(removeTextPhoneNumber, msg)
                else:
                    flash(removed)
                    return redirect(url_for('unsubscribe'))
    
            if removeCallPhoneNumber:
                removed = mySubscription.unsubscribeCall(address, removeCallPhoneNumber)
                if not removed:
                    msg = getSetting("UnsubscribeMessage", "call").format(address)
                    myTwilioContact.sendTwilioUnsubscribeCall(removeCallPhoneNumber, msg)
                else:
                    flash(removed)
                    return redirect(url_for('unsubscribe'))
 
            if config.isProduction:
                tracker_primary.send('event', 'Unsubscribe', 'Successfully Unsubscribed')
                tracker_secondary.send('event', 'Unsubscribe', 'Successfully Unsubscribed')

            return render_template("remove.html", removeEmailAddress=removeEmailAddress, removeTextPhoneNumber=removeTextPhoneNumber, removeCallPhoneNumber=removeCallPhoneNumber)
     
    except Exception as e:
        logger.critical("Traceback: %s" % traceback.format_exc())
        flash(getSetting("ErrorMessage", "unsubscribe"))
        return redirect(url_for('unsubscribe'))
