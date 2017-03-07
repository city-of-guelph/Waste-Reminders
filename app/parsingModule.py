from app import datetime, timedelta
from validationModule import changeDate
from settingsModule import getSetting
import collections
from config import DATA_IDINFO, DATA_WEEK_A_SCHEDULE, DATA_WEEK_B_SCHEDULE, \
    DATA_WEEK_Z_SCHEDULE, DATA_ADDRESS_LIST, DATA_SPECIAL_EVENTS, DATA_STAT_HOLIDAYS


def getIDInfo(idNum):
    IDInfoFile = open(DATA_IDINFO) #open the file which pairs address id's with collection schedules and days
    data = []
    originalDays = []
    newDays = []
    schedule = ""
    for line in IDInfoFile: # a typical line looks like ID - W_ - dayNumber
        data.append(line.split(' - ')) #append the list [ID, W_, dayNumber]
    for i in data:
        if i[0] == str(idNum): # if the id in the triple matches what you're looking for
            originalDays = i[2].strip().split(';') #e.g. '2';'3';'4';'5';'6' -> ['2','3','4','5','6']
            schedule = i[1] # something like 'WA', 'WB', 'WZ', 'ZZ'
    for x in range(0,len(originalDays)): #for each numerical day
        if originalDays[x] == '1':
            newDays.append('Sunday')
        if originalDays[x] == '2':
            newDays.append('Monday')
        if originalDays[x] == '3':
            newDays.append('Tuesday')
        if originalDays[x] == '4':
            newDays.append('Wednesday')
        if originalDays[x] == '5':
            newDays.append('Thursday')
        if originalDays[x] == '6':
            newDays.append('Friday')
        if originalDays[x] == '7':
            newDays.append('Saturday') # add it day name equivalent to newDays
    if schedule == 'WA':
        schedule = "Week A"
    if schedule == 'WB':
        schedule = "Week B"
    if schedule == 'WZ':
        schedule = "Week Z"
    if schedule == 'ZZ':
        schedule = None

    return({'newDays': newDays, 'schedule': schedule, 'originalDays': originalDays})


def getSchedule(scheduleType, pickupDates):
    schedFile = None
    data = []
    dataToSend=[]
    bgColor = '#FF0000'
    cartColors = []
    cartColorsToSend = []
    if scheduleType == 'Week A':
        schedFile = open(DATA_WEEK_A_SCHEDULE)
    elif scheduleType == 'Week B':
        schedFile = open(DATA_WEEK_B_SCHEDULE)
    elif scheduleType == 'Week Z':
        schedFile = open(DATA_WEEK_Z_SCHEDULE)

    if schedFile == None: #if the week was 'Please contact the city.' (ZZ)
        return

    for line in schedFile: #date - some of ('L','R','O','S') separated by ;
        data.append(line.strip().split(' - '))

    for x in data:
        cartList = []
        cartList = x[1].strip().split(';') # -> e.g. ['L','O','S']

        #bgColor is for the calendarCell, cartColors self explanatory

        if 'L' in cartList and 'R' in cartList: # week Z pickups
            bgColor = getSetting('Calendar','dualBackground')
            cartColors = ['GREY', 'BLUE']
        elif 'L' in cartList:
            bgColor = getSetting('Calendar','greyBackground')
            cartColors = ['GREY']
        elif 'R' in cartList:
            bgColor = getSetting('Calendar','blueBackground')
            cartColors = ['BLUE']
        else:
            bgColor = '#000000' #black, this should never happen

        if changeDate(x[0]) in pickupDates: #if we just processed the date that coincides with a pickup date, add the colors list to a final list
            cartColorsToSend.append(cartColors)

        maxDate = datetime.strptime(str(pickupDates[len(pickupDates) - 1]), '%Y-%m-%d').date()
        addDays = 7 - (maxDate.isoweekday() % 7)
        maxDate = maxDate + timedelta(days=addDays)
        maxDate = maxDate.strftime('%Y-%m-%d')
        if changeDate(x[0]) >= pickupDates[0] and changeDate(x[0]) <= maxDate:
            dataToSend.append([changeDate(x[0]), bgColor]) # tack on the date and background color to a final list

    return [dataToSend, cartColorsToSend] #one list will be used for cell background, the other for making pickup events


def generateStatHolidays():
    sd = []
    for line in open(DATA_STAT_HOLIDAYS):
        sd.append(datetime.strptime(line.strip(), '%d/%m/%Y').date().isoformat())
    return sd


def generateHomepageDropdown():
    addressFile = open(DATA_ADDRESS_LIST)
    myDict = {}
    for line in addressFile:
        data = line.strip().split(' - ')
        myDict[data[0].upper()] = data[1].upper()
    return collections.OrderedDict(sorted(myDict.items()))


def generateSeasonalEvents():
    events = []
    elems = open(DATA_SPECIAL_EVENTS).read().splitlines()
    for i in range(0,len(elems),4):
        name = elems[i]
        start = changeDate(elems[i+1])
        end = changeDate(elems[i+2])
        desc = elems[i+3]
        events.append([name,start,end,desc])
    return events
