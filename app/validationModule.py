from app import date
from settingsModule import getSetting

def changeDate(date):
    # changes date format from dd/mm/yyyy to yyyy-mm-dd
    return date[-4:] + '-' + date[3:5] + '-' + date[:2]

def militaryToStandard(time):
    
    if not time:
        return "7:00 PM"
    
    newTime = int(time)
    
    if newTime == 0:
        return "12:00 AM"
    elif newTime > 0 and newTime < 12:
        return "%d:00 AM" % (newTime)
    elif newTime == 12:
        return "12:00 PM"
    else:
        return "%d:00 PM" % (newTime % 12)

def validateForm(email, textNumber, phoneNumber):
    messages = []
    if not phoneNumber and not email and not textNumber:
        messages.append(getSetting('Signup','noEmailOrPhone')+'\n')
    if textNumber and len(textNumber) != 10:
        messages.append(getSetting('Signup','invalidPhone')+'\n')
    if phoneNumber and len(phoneNumber) != 10:
        messages.append(getSetting('Signup','invalidPhone')+'\n')
    return messages


def validateOpts(optionalComms):
    messages = []
    if optionalComms == '00000':
        messages.append(getSetting('Signup','noNotificationsSelected')+'\n')
    return messages


def removeDuplicates(lst):
  newLst = []
  for i in lst:
    if i not in newLst:
      newLst.append(i)
  return newLst
