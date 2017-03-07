# Waste Reminder

A web application created in Python to allow residents to search for their weekly solid waste pickup schedule and signup for regular notifications via the following methods:

- Text msg
- Phone Call
- Email

## Getting Started

### Prerequisites

* Python 
    * 2.7.12
* Libraries
    * Flask
    * Flask-Security
    * SQLAlchemy
    * Twilio
    * APScheduler
* HTML / CSS / Javascript
    * Bootstrap
    * FullCalendar
    * Bootstrap DateTimePicker
* Database
    * SQLAlchemy

### Installing

Clone source form github.

Edit the ``` config.py ``` and replace any values marked as ``` <update> ``` to your own keys/settings.

From a command prompt in the project root folder run ``` pip install -r requirements.txt ``` which will install all needed libraries.

Initialize the database before running the application for the first time by typing  ``` python db_create.py ```.

To launch the application type ``` python run.py ``` which will open the app using the Flask built in webserver at ``` localhost:5000 ``` in debug mode.

### Data Files

The web application requires a number of TXT files which supplies the pickup schedule information as well as stat holidays and special events. The files are placed in the app/data folder.

Extracts from the City of Guelph's GIS system were supplied in CSV format, in order to make the data easier to work with they are run through a small conversion routine and converted to the required TXT files.

To run the conversion program, place the input CSV files into the ```app/data``` folder and from a command prompt run ``` python generateTXT.py```. A small menu is presented with options to select which file(s) to create.

NOTE - No sample CSV files are included with this package, it is recommended to produce the format of the TXT files directly and skip this middle conversion step.

### Updating Subscription Information

If there are route/schedule changes required, after generating new TXT files, the same generateTXT.py can be run to update existing Subscriptions in the sql database. Simply run the same ```python generateTXT.py``` from command line and select the last option (7).

## Running the tests

A number of unit tests are created in ```tests.py``` using the python [unittest](https://docs.python.org/2/library/unittest.html) framework.

These can be run from the project root folder: ``` python tests.py ```.

## Deployment

Python web applications can be deployed using a variety of methods, see the [Flask Deployment Documentation](http://flask.pocoo.org/docs/0.11/deploying/) for details.

The City of Guelph is deployed using gunicorn.

## Features
### User Interface

* Allows users to pick their address from a suggestion box
* Quick access to information about next collection day
* Full featured calendar that displays collection days and their respective cart colors
    * Also shows statutory holidays and special events, and gives users the ability to click events for more details
* Print a full page monthly calendar
* Export ICS files, for use in software such as Google Calendar, or Microsoft Outlook, and also to add to your phone calendar
* Sign up for email, SMS, and phone call reminders
    * Users can choose delivery time, and whether to receive optional communications

### Administrator Interface

* A password protected environment for administrators to make changes
* Provides a graphical user interface to create, read, update and delete registered users (No SQL required)
    * Comes with a search option to search the entries
* The file manager allows for the data files to be updated
    * For example, addresses, statutory holidays and seasonal events can be added and removed
* Can also send out alerts via email, SMS, and phone to those who opted in.
    * Schedule alerts to be sent out on a specific date and time
    * Delete alerts before they have been sent
* Logging information:
    * Users logging in/out of the admin panel
    * Scheduling of alerts
    * Deleting alerts
    * Successful processing of alerts
    * Successful send of regular notifications
* Message Logging:
    * A record is logged for each outgoing message of any time, including Twilio unique confirmation id

## Technical Details

### Error Reporting
* Log events with a level higher than ERROR are logged to a Slack channel
* All other informational/debug messages are logged to a local rotating log file, retention of 10 days, 1mb maximum file size

### Analytics
* Google Analytics are tracked for each page as well as Signup/Unsubscribe events

### Recaptcha
* Google Recaptcha is used on the signup page to deter bots

### Data

* Data files supplied by the City of Guelph in CSV files are run through a Python script to generate .txt files in a format that is more readily processed by the application
* Subscription/Alerts/Logging information is stored in a local DB managed by SQLAlchemy
