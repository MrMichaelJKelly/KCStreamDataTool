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
import getopt
import time
import re
import platform
from pathlib import Path
from xlrd import open_workbook, XLRDError, xldate
import xlrd

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
columnHeaders = [ 'Date', 'Temp.[C]', 'pH', 'EC[uS/cm]', 'D.O.[%]', 'D.O.[ppm]', 'Turb.FNU', 'Remarks', 'Other' ]

# Locate files to process
def collectFiles(inputFolder, outputFolder):
    filesToRead = []
    # Regular expression to identify files we are interested in processing
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
        
        # Process each data (log) file
        for file in logFiles:
            xlrdLogFileHandle.write("=== %s ===\n" % file)
            if not processLogFile(file, xlrdLogFile):
                xlrdLogFileHandle.write('Error processing %s\n' % file)
                ret = False
    finally:
        xlrdLogFileHandle.close()

    return ret

# Process one raw data file (a/k/a LogFile which is confusing, since it conflicts
# with XLRD's use of LogFile as a output of errors, warnings, etc.)
# the second parameter here is used for XLRD's log  messages
 
def processLogFile(rawDataFile, xlrdLog):
    
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
    
    # Some sanity checking
    if book.nsheets != 2 or not isinstance(siteName, str):
        print('Workbook not in expected format')
        xlrdLog.write('Workbook %s not in expected format\n' % (rawDataFile))
        return False
    
    if verbose:
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
        # Two variations:
        # Date	Temp.[?C]	pH 	EC[?S/cm]	D.O.[%]	    D.O.[ppm]	Turb.FNU	Remarks
        # Date	Temp.[?C]	pH 	D.O.[%]	    D.O.[ppm]	Turb.FNU	EC[?S/cm]
        # We've adopted the first one (which is the most common) as the standard, so if we
        # detect the second, we have to do move columns around as we emit them to the CSV
        # column
        
        nonStandardColumns = False

        if numColumns > 4 and sheet.cell(0, 4).ctype == 1 and sheet.cell(0, 4).value == 'D.O.[%]':
            nonStandardColumns = True           
                # Transpose columns if needed - column indices are in the
                # source sheet - they will be pulled from those source columns
                # and then written to columns 2, 3, 4 etc. - since 0 is the site name
                # and 1 is the file name.
                # Item      Standard Sheet      Weird Sheet
                # Temp          2                   2
                # ph            3                   3
                # EC[uS/cm]     4                   7
                # D.O.[%]       5                   4
                # D.O.[ppm]     6                   5
                # Turb.FNU      7                   6
                # Remarks       8                   8           
            colOrder = [0, 2, 3, 7, 4, 5, 6, 8]
            print("This sheet has non-standard column ordering; adjusting columns to match standard.\n")
        else:
            colOrder = [0, 2, 3, 4, 5, 6, 7, 8]
        
        nColsToWrite = len(colOrder)

        for rowIndex in range(1, sheet.nrows):    # Iterate through data rows
            if verbose:
                print ('-'*40)
                print ('Row: %s' % rowIndex)   # Print row number
            # Skip entirely blank rows
            if sheet.row_types(rowIndex).count(0) == numColumns:
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
                    # 3 == date per https://pythonhosted.org/xlrd3/cell.html
                    if (cellType == 3):
                        year, month, day, hour, minute, second = xldate.xldate_as_tuple(cellValue.value, book.datemode)
                        outputCSV.write('%4d-%02d-%02d' % (year, month, day))
                        d = datetime.date(year,month,day)
                        if (d < earliestDateSeen):
                            earliestDateSeen = d
                        if (d > latestDateSeen):
                            latestDateSeen = d
                        
                    elif (cellType in [1, 2]):   # 1 = text, 2 = number
                            # Other column - e.g. ph, Turb.FNU, etc.
                            outputCSV.write(str(cellValue.value))
                    else:
                        xlrdLog.write('%s: Unknown value type for [%s,%s] : %s\n' % (rawDataFile, rowIndex, columnIndex, cellType))
                    if (nCols < nColsToWrite):
                        outputCSV.write(',')        # append , except after last column value
                        
            # After emitting all columns, terminate the line
            outputCSV.write('\n')       # Terminate line
    else:
        print('Wrong # of sheets or first row of 2nd worksheet is not Date.. skipping')
        ret = False
       
    print('%d rows.' % sheet.nrows)
        
    if ret:
        siteData = SiteData(rawDataFile, minDate=earliestDateSeen, maxDate=latestDateSeen, numRecs=nRows)
        if siteName not in sites:
            # Not in list yet - add a tuple
            print("New site encountered: " + siteName)
            sites[siteName] = [ siteData ]
        else:
            print("Additional data for site: " + siteName)
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

    try:
        opts, args = getopt.getopt(argv,"vhi:o:",["verbose", "help", "input=", "help", "output="])
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

    if inputFolder == '':
        helpMesssage()

    outputPath = os.path.join(outputFolder, 'StreamData.CSV')
    try:
        outputCSV = open(outputPath, 'w')
    except IOError as e:
        print('Error opening '+outputPath,': '+ str(e))
        exit(-1)
    
    print('Processing LOG file data in "'+ inputFolder+ '"...')
    print('Writing to "'+ outputPath+ '"...')
   
    files = collectFiles(inputFolder, outputFolder)
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
