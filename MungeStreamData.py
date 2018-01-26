#!/usr/bin/env python3
#
# Script to read a bunch of data files with measurements from
# streams and consolidate them, standardize format, eliminate
# duplicate data readings, etc.
#
# Mike Kelly - December 2017

import os
from collections import namedtuple
import sys
import glob
import ctypes
import datetime
from dateutil.parser import parse
import getopt
import heapq
import time
import re
import platform
from pathlib import Path
from xlrd import open_workbook, XLRDError, xldate
import xlrd
import csv

#import xlrd
#book = xlrd.open_workbook("myfile.xls")
#print("The number of worksheets is {0}".format(book.nsheets))
#print("Worksheet name(s): {0}".format(book.sheet_names()))
#sh = book.sheet_by_index(0)
#print("{0} {1} {2}".format(sh.name, sh.nrows, sh.ncols))
#print("Cell D30 is {0}".format(sh.cell_value(rowx=29, colx=3)))
#for rx in range(sh.nrows):
#    print(sh.row(rx))

# Files to exclude from if present
filesToExclude = ['.dropbox', 'desktop.ini' ]

# Dictionary of sites encountered - to look for dupes - the value is a SiteData named tuple containing
# path name to the file and the dates for which we have data
sites = {}

# Each item in sites has site meta data:
# filePath - path to file containing data on this site
# minDate - earliest date data was found for the site
# maxDate - latest date data was found for the site
# numRecs - number of data records for the site
SiteData = namedtuple('SiteMetadata', 'filePath, minDate, maxDate, numRecs')

verbose = False

# handle to output CSV file
outputCSV = None

# Standard data headers - some are in a slightly different format and have to be massaged a bit...
columnHeaders = [ 'Date', 'Time', 'Temp.[C]', 'pH', 'mV [pH]', 'EC[uS/cm]', 'D.O.[%]', 'D.O.[ppm]', 'Turb.FNU', 'Remarks', 'Other' ]

# This list is 1:1 with columnHeaders and shows which columns we should calculate a median for.
# The medians are calculated per site/per date.
calculateMedians = [ False, False, True,      True, True,       True,        True,      True,        True,       False,      False ]


# Locate files to process - if doTemperature is True, doing temperature
# files - otherwise LOG files
def collectFiles(inputFolder, outputFolder, doTemp):
    filesToRead = []
    # Regular expression to identify files we are interested in processing - for
    # Temperature data, it is CSV's; for log files, it is .XLS files
    if doTemp:
        logFilePattern = re.compile('.*\.csv$')
    else:
        logFilePattern = re.compile('.*\.xls$')
        
    for subdir, dirs, files in os.walk(inputFolder):
        for file in files:
            if file not in filesToExclude:
                # Check if this file matches the pattern for a log file to
                # process
                if verbose:
                    print("Checking "+os.path.join(subdir,file))
                m = re.match( logFilePattern, file)
                if m:
                    if verbose:
                        print('Adding '+os.path.join(subdir, file))
                    filesToRead.append(os.path.join(subdir, file))
                elif verbose:
                        print('Skipping '+os.path.join(subdir, file))
                    
    return filesToRead

# Thanks to https://stackoverflow.com/questions/7619319/python-xlrd-suppress-warning-messages
class XlrdLogFileFilter(object):
    def __init__(self, mylogfile=sys.stdout, skip_list=()):
        self.f = mylogfile
        self.state = 0
        self.skip_list = skip_list
    def write(self, data):
        if self.state == 0:
            found = any(x in data for x in self.skip_list)
            if not found:
                self.f.write(data)
                return
            if data[-1] != '\n':
                self.state = 1
        else:
            if data != '\n':
                self.f.write(data)
            self.state = 0

# Class to find median of a string of values
# from https://discuss.leetcode.com/topic/27521/short-simple-java-c-python-o-log-n-o-1/2 and
# https://discuss.leetcode.com/topic/27689/python-o-lgn-using-two-heapq-data-sturctures
# It uses two priority heaps to divide the values as they arrive - a priority heap is a
# balanced binary tree of values.
#
class MedianFinder(object):

    def __init__(self):
        self.small = []
        self.large = []

    def addNum(self, num):
        if len(self.small) == 0:
            heapq.heappush(self.small, -num)
            return
        if num <= -self.small[0]:
            # push to small part
            heapq.heappush(self.small, -num)
        else:
            # push to large part
            heapq.heappush(self.large, num)
        # adjust small and large balance
        if len(self.small) - len(self.large) == 2:
            heapq.heappush(self.large, -heapq.heappop(self.small))
        elif len(self.small) - len(self.large) == -2:
            heapq.heappush(self.small, -heapq.heappop(self.large))

    def findMedian(self):  
        if len(self.small) == len(self.large):
            return (self.large[0] - self.small[0])/2.0
        return -float(self.small[0]) if len(self.small) > len(self.large) else float(self.large[0])

# A list of values for a particular site/item by date
# Designed to be put in a list indexed by site and item.
# Used to calculate medians after all values have been recorded
class SiteItemMeasurements(object):

    # Create a holder for a list of median values for a particular measurement for a
    # particular site.  The list has the values for each date.
    def __init__(self, site, item):
        self.siteName = site
        self.itemName = item
        self.medianFinders = {}
    
    def recordValue(self, dt, val):
        global verbose
        if dt not in self.medianFinders:      # first time we are seeing this date
            # A MedianFinder is an accumulator for a particular measurement on a
            # particular date - each value is recorded in the MedianFinder as it
            # is seen, and at the end we can ask the MedianFinder to find the median
            # of all values recorded along the way.
            
            # Special case - if we have a date one day on either side, consider them
            # equivalent and just normalize to whichever one we see first, i.e.
            # 6/29/15, 6/30/15 and 7/1/15 will all be considered the same and recorded
            # under one of those dates, whichever is the first one we encounter in the
            # data stream
            dtPrevious = parse(dt) + datetime.timedelta(days=-1)
            strDatePrevious = '%4d-%02d-%02d' % (dtPrevious.year, dtPrevious.month, dtPrevious.day)
            dtNext = parse(dt) + datetime.timedelta(days=1)
            strDateNext = '%4d-%02d-%02d' % (dtNext.year, dtNext.month, dtNext.day)
            if strDatePrevious in self.medianFinders:
                dt = strDatePrevious
            elif strDateNext in self.medianFinders:
                dt = strDateNext
            self.medianFinders[dt] = MedianFinder()
        self.medianFinders[dt].addNum(val)
        if verbose:
            print('recordValue: recorded %f for %s' % (val, dt))
    
    # Calculate the medians for each date by enumerating the
    # dates for which values have been recorded and using the
    # medianFinder for that date to find the median for this value
    # on that date.  Returns a dictinoary of median values indexed
    # by date, e.g.
    # medians['06/30/2017'] = 13.26
    def calcMedians(self):
        medians = {}
        for dt in self.medianFinders.keys():
            medians[dt] = self.medianFinders[dt].findMedian()
        return medians

# This list consists of MedianValue objects that record values per-site, per-date for each item marked
# above as needing a median.  
class MedianCollector(object):
    
    siteMeasurementValues = {}
    
    def addMeasurement(self, site, dt, item, val):
        global verbose
        if verbose:
            print('Recording %s as %f' % (item, val))
        if site not in self.siteMeasurementValues:      # first time we are seeing this site
            self.siteMeasurementValues[site] = {}
        if item not in self.siteMeasurementValues[site]:    # first time for this measurement
            # Don't yet have a tracker for this item for this site - add it
            self.siteMeasurementValues[site][item] = SiteItemMeasurements(site, item)
        # Now record the value for this item on this date at this site
        self.siteMeasurementValues[site][item].recordValue(dt, val)

    def emitMedianValuesCSV(self, outputCSVFile):
        for site, siteCollection in self.siteMeasurementValues.items():
            for item, itemCollection in siteCollection.items():
                for dt, medianValue in itemCollection.calcMedians().items():
                    outputCSVFile.write('%s,"%s",%s,%f\n' % (site, item, dt, medianValue))

# Process the Temperature data CSV files found.
# Input CSV files are in two different formats:
# The first is for the loggers that only collect temperature, they read 
#
#"Plot Title: Caldwell_Mouth"
#"#","Date Time, GMT-07:00","Temp, ?F (LGR S/N: 10360568, SEN S/N: 10360568)","Coupler Detached (LGR S/N: 10360568)","Coupler Attached (LGR S/N: 10360568)","Stopped (LGR S/N: 10360568)","End Of File (LGR S/N: 10360568)"
#1,11/03/23 02:30:00 AM,68.828,Logged,,,
#2,11/03/23 03:00:00 AM,67.413,,,,
#3,11/03/23 03:30:00 AM,69.300,,,,
#
# The second file type is for loggers that collect both temperature and dissolved oxygen, they look like:
#
#"Plot Title: Yellowhawk Old Milton Hiway"
#"#","Date Time, GMT-07:00","DO conc, mg/L (LGR S/N: 11009651, SEN S/N: 11009651)","Temp, ?F (LGR S/N: 11009651, SEN S/N: 11009651)","Coupler Attached (LGR S/N: 11009651)","Stopped (LGR S/N: 11009651)","End Of File (LGR S/N: 11009651)"
#1,05/21/17 01:31:27 PM,11.11,58.10,,,
#2,05/21/17 02:31:27 PM,10.89,59.43,,,
#3,05/21/17 03:31:27 PM,10.61,60.58,,,
#
# This routine reads both formats and emits a CSV file with this format:
#
# Site,"Date Time, GMT-07:00","DO conc, mg/L","Temp, DegF","Source File"
#
def processTemperatureFiles(temperatureFiles, logFile):
    ret = True      # optimistic
    
    try:    
        # Write the CSV header row
        outputCSV.write('Site, "Date Time, GMT-07:00","DO conc, mg/L","Temp, DegF", "RawDataFile"\n')
       
        # Process each data (temperature) file
        for file in temperatureFiles:
            logFile.write("=== %s ===\n" % file)
            if not processTemperatureFile(file, logFile):
                ret = False
    finally:
        logFile.close()

    return ret


# Process one raw data temperature file 
def processTemperatureFile(rawDataFile, logFile):
    
    global sites, outputCSV
    nRows = 0           # Number rows written to output
    ret = True
    
    print('processTemperatureFile: Processing '+rawDataFile)
    try:
        with open(rawDataFile) as csvfile:
            datarows = csv.reader(csvfile)
            for row in datarows:
                if nRows == 0:      # Site name - after "Plot Name: " on first row.  Sigh.
                                    # Too bad whoever did this had no $*#*$*$ idea what a
                                    # well-formed CSV file is supposed to look like.
                    siteName = row[0][16:]
                    # Some of the CSV files have a trailing " - remove it
                    if len(siteName) > 1 and siteName[-1] == '"':
                        siteName = siteName[:-1]
                    print ('Site name in data file: '+siteName)
                else:
                    numColumns = len(row)
                    if numColumns >= 7:
                        # Determine which flavor of format we've got based on CSV header
                        if nRows == 1:
                            if row[2][:2] == "DO":
                                # Flavor with DO in row
                                hasDO = True
                            elif nRows == 1 and row[2][:4] == "Temp":
                                # Flavor with only temperature
                                hasDO = False
                            else:
                                # Some other format
                                ret = False
                        else:
                            # Data rows
                            if hasDO:
                                # Flavor with DO in row
                                temp = row[3]
                                do = row[2]
                            else:
                                # Flavor with only temperature
                                do = ""
                                temp = row[2]
                    else:
                        # some unexpected format
                        ret = False
                        
                    if not ret:
                        print('CSV has non-standard format - skipping file')
                        logFile.write('CSV has non-standard format - skipping file\n')
                    elif nRows > 1:
                        # Skip first two rows that are headers - emit data for rows 2... n
                        outputCSV.write('{},{},{},{},{}\n'.format(siteName, row[1], temp, do, rawDataFile))
                        ret = True
                nRows += 1
                
                # If encountered a format error - skip out
                if not ret:
                    return ret
                
    except csv.Error as e:
        print('Error opening CSV file: %s\n' % (str(e)))
        logFile.write('Error opening CSV file {} (line {}): {}\n'.format(rawDataFile, datarows.line_num, e))
        ret = False
        
    if ret:
        print('%d data rows read.' % nRows)
        logFile.write('%d data rows read.\n' % nRows)
        
    return ret
    
# Process the log files found
def processLogFiles(logFiles):
    ret = True      # optimistic
    
    xlrdLogFileHandle = open("xlrd_log_file.txt", "w+")
    skip_these = (
        "WARNING *** OLE2 inconsistency",
        )
    try:        
        xlrdLogFile = XlrdLogFileFilter(xlrdLogFileHandle, skip_these)
        
        # Write the CSV header row
        outputCSV.write('Site, RawDataFile,')
        for colName in columnHeaders:
            outputCSV.write(colName+',')
        outputCSV.write('\n')

        medianCollector = MedianCollector()       
        
        # Process each data (log) file
        for file in logFiles:
            xlrdLogFileHandle.write("=== %s ===\n" % file)
            if not processLogFile(file, xlrdLogFile, medianCollector):
                xlrdLogFileHandle.write('Error processing %s\n' % file)
                ret = False
    finally:
        xlrdLogFileHandle.close()
        
    # Emit the median values for each measurement to the CSV
    outputCSV.write('\n\nMEDIAN VALUES\nSite,Measurement,Date,Median\n')
    medianCollector.emitMedianValuesCSV(outputCSV)

    return ret

# Process one raw data file (a/k/a LogFile which is confusing, since it conflicts
# with XLRD's use of LogFile as a output of errors, warnings, etc.)
# the second parameter here is used for XLRD's log  messages
 
def processLogFile(rawDataFile, xlrdLog, medianCollector):
    
    global sites, outputCSV
    nRows = 0           # Number rows written to output
    earliestDateSeen = datetime.date.max        # set to HIGHEST date so the first one we encounter is less
    latestDateSeen = datetime.date.min
    ret = True
    
    print('processLogFile: Processing '+rawDataFile)
    try:
        book = open_workbook(rawDataFile, logfile=xlrdLog)
    except XLRDError as e:
        print('Error opening workbook: %s\n' % (str(e)))
        xlrdLog.write('Error opening workbook %s: %s\n' % (rawDataFile, str(e)))
        return False
    
    sheet = book.sheet_by_index(0)
    # Site is always B19 per Evan
    siteName = sheet.cell_value(rowx=18, colx=1)

    # Some sanity checking - is the book in the expected format?
    if book.nsheets != 2 or not isinstance(siteName, str):
        print('Workbook not in expected format')
        xlrdLog.write('Workbook %s not in expected format\n' % (rawDataFile))
        return False

    print ('Site name in data file: '+siteName)
    
    # Map some sitenames together
    siteName = siteName.upper()
    siteMap = {'WHISI' : 'WHIRU',
               'WHRZ' : 'WHISP',
               'RUTZP.OUT' : 'RUTZP.outflow',
               'WHIRS' : 'WHISP',
               'WHIRZ' : 'WHISP',
               'RUTZPOND' : 'RUTZP',
               'YELPER' : 'YELPR',
               'RUTZEROUT' : 'RUTZP.outflow'
    }
    
    siteName = siteMap.get(siteName, siteName)
    
    print ('Site name: '+siteName)

    # Open the sheet and grab the data, copying it to the output CSV
    try:
        dataSheet = book.sheet_by_index(1)
        if verbose:
            print('Sheets: ',book.sheet_names())

    except XLRDError as e:
        print('Workbook does not have correct number of sheets')
        xlrdLog.write('Error getting data sheet for '+rawDataFile+' - Skipping Workbook for "'+siteName+'"\n')
        return False

    # Switch to data sheet
    sheet = book.sheet_by_index(1)
    
    # Get first line from sheet and analyze
    numColumns = sheet.ncols   # Number of columns
    
    # Check if workbook seems to match expected format:
    # 2 sheets
    # first cell in 2nd sheet has Date in the name
    if sheet.cell_value(rowx=0,colx=0) == u'Date' and book.nsheets == 2:
        # Print header row
        # [outputCSV.write(sheet.cell(0,x).value+',') if x < numColumns-1 else outputCSV.write(sheet.cell(0,x).value+'\n') for x in range(0, numColumns)]
        # Check to see if we have one of those books where the data doesn't match - in that case we have to do
        # some magic transposing
        # Three variations:
        # Date  Time	Temp.[C]	pH 	EC[uS/cm]	D.O.[%]	    D.O.[ppm]	Turb.FNU	Remarks
        # Date	Time    Temp.[C]	pH 	D.O.[%]	    D.O.[ppm]	Turb.FNU	EC[uS/cm]   Remarks
        # Date	Time	Temp.[C]	pH 	mV[pH]	    EC[uS/cm]	D.O.[%]	    D.O.[ppm]	Turb.FNU	Remarks
        # 0     1       2           3   4           5           6           7           8           9

        # We've adopted the third one (which is the most complete) as the standard, so if we
        # detect the others, we have to do move columns around as we emit them to the CSV
        # columns in the right order.
        
        columnFormatModel = None

        if numColumns > 4 and sheet.cell(0, 4).ctype == 1 and sheet.cell(0, 4).value == 'D.O.[%]':
            columnFormatModel = 1           
                # Transpose columns if needed - column indices are in the
                # source sheet - they will be pulled from those source columns
                # and then written to columns 2, 3, 4 etc. - since 0 is the site name
                # and 1 is the file name.  -1 means blank column (skip)
            colOrder = [0, 1, 2, 3, -1, 7, 4, 5, 6, 8]
            print("This sheet has non-standard column ordering; adjusting columns to match standard.\n")
        elif numColumns > 4 and sheet.cell(0, 4).ctype == 1 and sheet.cell(0, 4).value == 'mV[pH]':
            columnFormatModel = 0
            colOrder = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        elif numColumns > 4 and sheet.cell(0, 5).ctype == 1 and sheet.cell(0, 5).value == 'D.O.[%]':
            columnFormatModel = 2
            colOrder = [0, 1, 2, 3, -1, 4, 5, 6, 7, 8]
        else:
            print('Workbook has non-standard column headers - see columnFormatModel in processLogFile to address - skipping workbook')
            xlrdLog.write('Workbook has non-standard column headers - see columnFormatModel in processLogFile to address - Skipping Workbook for "'+siteName+'"\n')
            return False 
        
        nColsToWrite = len(colOrder)

        for rowIndex in range(1, sheet.nrows):    # Iterate through data rows
            if verbose:
                print ('-'*40)
                print ('Row: %s' % rowIndex)   # Print row number
            # Skip entirely blank rows
            rowIsBlank = True
            for columnIndex in range(1, sheet.ncols):  # Iterate through columns
                val = sheet.cell(rowIndex, columnIndex)
                if (val.ctype != 0 or (val.ctype == 1 and len(str(val)) > 0)):
                    rowIsBlank = False
                    
            if rowIsBlank:
                if verbose:
                    print('Skipping blank row')
                continue
            else:
                nRows += 1              
  
            nCols = 0           # Number of columns processed - so we can omit the last "," in the CSV output
            
            for columnIndex in colOrder:  # Iterate through columns
                nCols += 1
                if columnIndex >= numColumns:
                    continue            # don't access columns that don't exist on this sheet
                elif columnIndex == -1:     # emit a blank column - this isn't in source sheet
                    outputCSV.write(',')
                    continue
                else:
                    cellValue = sheet.cell(rowIndex, columnIndex)  # Get cell object by row, col
                    cellType = cellValue.ctype
                    
                    # Prefix each row with the site name of the data and the
                    # file name it came from
                    if (columnIndex == 0):
                        outputCSV.write(siteName+','+rawDataFile+',')
                        
                    if verbose:
                        print ('Column: [%s] is [%s] : [%s]' % (columnIndex, cellType, cellValue))
                        
                    # Somewhere these numeric values have to be defined, right?
                    # 3 == date per https://pythonhosted.org/xlrd3/cell.html - but there are two
                    # in the data, a date and a time.  0 is he date, 1 is the time.  Sigh.
                    if (cellType == 3):
                        if (columnIndex == 0):      # Date
                            # Date
                            year, month, day, hour, minute, second = xldate.xldate_as_tuple(cellValue.value, book.datemode)
                            strDate = '%4d-%02d-%02d' % (year, month, day)
                            outputCSV.write(strDate)
                            d = datetime.date(year,month,day)
                            if (d < earliestDateSeen):
                                earliestDateSeen = d
                            if (d > latestDateSeen):
                                latestDateSeen = d
                        else:  # Only other date value in input is the Time stamp
                            # Just emit time as is.
                            outputCSV.write(str(cellValue.value))
                        
                    elif (cellType in [1, 2]):   # 1 = text, 2 = number
                            # Other column - e.g. ph, Turb.FNU, etc.
                            outputCSV.write(str(cellValue.value))
                            # Do we need to accumulate values for this for median calculation?
                            # Note some measurements have '-----' instead of 0 for missing values
                            # so catch that here by checking only for numeric values
                            if cellType == 1:
                                measurementValue = 0
                            else:
                                measurementValue = cellValue.value
                            if calculateMedians[columnIndex]:
                                medianCollector.addMeasurement(siteName, strDate, columnHeaders[columnIndex], measurementValue)
                    else:
                        xlrdLog.write('%s: Unknown value type for [%s,%s] : %s\n' % (rawDataFile, rowIndex, columnIndex, cellType))
                    if (nCols < nColsToWrite):
                        outputCSV.write(',')        # append , except after last column value                    
                        
            # After emitting all columns, terminate the line in the CSV file
            outputCSV.write('\n')       # Terminate line
    else:
        print('Wrong # of sheets or first row of 2nd worksheet is not Date.. skipping')
        ret = False
       
    print('%d data rows read.' % sheet.nrows)
        
    if ret:
        siteData = SiteData(rawDataFile, minDate=earliestDateSeen, maxDate=latestDateSeen, numRecs=nRows)
        if siteName not in sites:
            # Not in list yet - add a tuple
            print("This data is for a new site: " + siteName)
            sites[siteName] = [ siteData ]
        else:
            print("This is additional data for site: " + siteName)
            sites[siteName].append(siteData)

    return ret
        
#print("The number of worksheets is {0}".format(book.nsheets))
#print("Worksheet name(s): {0}".format(book.sheet_names()))
#sh = book.sheet_by_index(0)
#print("{0} {1} {2}".format(sh.name, sh.nrows, sh.ncols))
#print("Cell D30 is {0}".format(sh.cell_value(rowx=29, =3)))
#for rx in range(sh.nrows):

 
def helpMessage():
      print('MungeStreamData.py [-o <outputFolder>] -i <inputFolder>')
      print('Processes all data files under <inputFolder>')
      print('Output goes to specified output folder, default is ProcessedStreamData')
      sys.exit(2)


def main(argv):
   
   # Only supporting Windows for now...
    if (platform.system() != 'Windows'):
        print('Sorry, this script is supported only on Windows for now... bug Mike')
        sys.exit(2)

   # Default output folder
    global verbose
    global outputCSV
    global sites
   
    outputFolder = 'ProcessedStreamData'
    inputFolder = '.'
    doTemperature = False

    try:
        opts, args = getopt.getopt(argv,"vhi:o:t",["verbose", "help", "input=", "help", "output=", "temp"])
    except getopt.GetoptError:
        helpMessage()
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            helpMessage()
        if opt in ("-v", "--verbose"):
            verbose = True
        elif opt in ("-o", "--output"):
            outputFolder = arg
        elif opt in ("-i", "--input"):
            inputFolder = arg
        elif opt in ("-t", "--temp"):
            doTemperature = True

    if inputFolder == '':
        helpMesssage()
        
    if doTemperature:
        outputPath = os.path.join(outputFolder, "TemperatureData.CSV")
        logPath = os.path.join(outputFolder, "TemperatureLogFile.txt")
    else:
        outputPath = os.path.join(outputFolder, 'StreamData.CSV')
        
    try:
        outputCSV = open(outputPath, 'w')
    except IOError as e:
        print('Error opening '+outputPath,': '+ str(e))
        exit(-1)
    
    if doTemperature:
        try:
            outputLogFile = open(logPath, 'w')
        except IOError as e:
            print('Error opening '+logPath,': '+ str(e))
            exit(-1)
        print('Processing Temperature file data in "'+ inputFolder+ '"...')
    else:
        print('Processing LOG file data in "'+ inputFolder+ '"...')
        
    print('Writing to "'+ outputPath+ '"...')
   
    files = collectFiles(inputFolder, outputFolder, doTemperature)
    if doTemperature:
        processTemperatureFiles(files, outputLogFile)
    else:
        processLogFiles(files)

    print('Done!')
    
    # Dump out collected per-site data
    for site in sites:
        print('For "' + site +'"')
        for item in sites[site]:
            print('\tData from %s to %s' % (str(item.minDate), str(item.maxDate)))
            print('\t%d records from: %s' % (item.numRecs, item.filePath))
        print('-'*50)
   

if __name__ == "__main__":
   main(sys.argv[1:])
