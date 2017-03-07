import csv, sys
from app import app, Subscription, getIDInfo, removeDuplicates


def __statHolidays():
    f=open('statutory_holidays.csv')
    g=open('StatHolidays.txt','w')
    reader = csv.reader(f)

    i = 0
    for row in reader:
        if i == 0:
            i+=1
            continue
    
        g.write(row[0].strip() + '\n')

    f.close()
    g.close()
    print("Successfully generated statutory holidays file.")


def __address():
    f=open('street_address.csv')
    g=open('addressList.txt','w')
    reader = csv.reader(f)
    
    
    addresses = []
    i = 0
    for row in reader:
        if i == 0:
            i+=1
            continue
        newRow = row[2].strip() + ' ' + row[1].strip()
        if row[7].strip():
            newRow += ', ' + row[7].strip()
            
        newRow += ' - ' + row[0].strip() + '\n'
        
        g.write(newRow)
    
    f.close()
    g.close()
    print("Successfully generated addresses file.")


def __IDInformation():
    f=open('address_collection.csv')
    g=open('IDInfo.txt','w')
    reader = csv.reader(f)
    
    i = 0
    for row in reader:
        if i == 0:
            i+=1
            continue
    
        g.write(row[0].strip() + ' - ' + row[1].strip() + ' - ' + row[2].strip() + '\n')
    
    f.close()
    g.close()
    print("Successfully generated ID information file.")


def __schedules():
    f=open('collection_schedule.csv')
    wa=open('WeekASchedule.txt','w')
    wb=open('WeekBSchedule.txt','w')
    wz=open('WeekZSchedule.txt','w')
    reader = csv.reader(f)
    
    i = 0
    for row in reader:
        if i == 0:
            i+=1
            continue
        #print(row)
        weekIdentifier = row[0]
        outFile = None
        if weekIdentifier == 'WA':
            outFile = wa
        elif weekIdentifier == 'WB':
            outFile = wb
        elif weekIdentifier == 'WZ':
            outFile = wz
        
        if row[2] != '':
            outFile.write(row[1].strip() + ' - ' + row[2].strip() + '\n')
    
    f.close()
    wa.close()
    wb.close()
    wz.close()
    print("Successfully generated schedule files for all 3 weeks.")


def __updateSubscriptions():
    mySubscription = Subscription()
    subscriptions = mySubscription.query.all()
    subscriptions = removeDuplicates(subscriptions)
            
    for sub in subscriptions:
        addressInfo = getIDInfo(sub.address_id)
        daysString = ''.join(addressInfo['originalDays'])
        mySubscription.updateScheduleByAddressId(sub.address_id, addressInfo['schedule'], daysString)
        print("Subscription Updated: %s" % sub.address_id)
        
    
def runGenerate():
    while (1):
        print("\nWelcome to the File Generation Utility.")
        print("Please ensure the appropriate CSV file(s) are in the same directory as this script.\n")
        print("Please enter one of the following numbers:")
        print("1. Create a file from 'street_address' data file.\n\tThis file will contain addresses and their ID's.")
        print("2. Create a file from 'address_collection' data file.\n\tThis file will contain ID's, and their schedule type and collection days.")
        print("3. Create 3 files from 'collection_schedule' data file.\n\tThese files will contain dates and carts for each week type (Week A, B, Z).")
        print("4. Create a file from 'statutory_holidays' data file.\n\tThis file will contain statutory holidays for the year.")
        print("5. Create 2 files reflecting an updated database of addresses.\n\tThe files created will be addressList.txt and IDInfo.txt.")
        print("6. Create all necessary text files.\n\tThis will perform operations 1 - 4 above.")
        print("7. Update schedule for current subscriptions.")
        print("8. Exit")
        
        cmd = input("Please enter a number: ")
        
        try:
            cmd = int(cmd)
        except:
            pass
        
        if cmd == 1:
            __address()
            print("Your files were placed where this script is located.")
        elif cmd == 2:
            __IDInformation()
            print("Your files were placed where this script is located.")
        elif cmd == 3:
            __schedules()
            print("Your files were placed where this script is located.")
        elif cmd == 4:
            __statHolidays()
            print("Your files were placed where this script is located.")
        elif cmd == 5:
            __address()
            __IDInformation()
            print("Your files were placed where this script is located.")
        elif cmd == 6:
            __address()
            __IDInformation()
            __schedules()
            __statHolidays()
            print("Your files were placed where this script is located.")
        elif cmd == 7:
            __updateSubscriptions()
        elif cmd == 8:
            exit()
        else:
            print("***Please enter valid input.***")
        
        keepGoing = input("\nWould you like to continue? (Y/N): ")
        if keepGoing.upper() != 'Y':
            exit()
