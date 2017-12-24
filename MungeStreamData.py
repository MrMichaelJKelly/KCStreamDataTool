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
import ctypes
import datetime
import getopt
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

# Hash of sites encountered - to look for dupes - the value is a list containing
# path name to the file and the dates
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

# Locate files to process
def collectFiles(inputFolder, outputFolder):
    filesToRead = []
    # Regular expression to identify files we are interested in processing
    logFilePattern = re.compile('LOG.*\.xls')
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

# Process the log files found
def processLogFiles(logFiles):
    ret = True      # optimistic
    
    for file in logFiles:
        if not processLogFile(file):
            print('Error processing '+file)
            ret = False
    return ret
        

def processLogFile(logFile):
    
    global sites, outputCSV
    
    if verbose:
        print('Processing '+logFile)
    try:
        book = open_workbook(logFile)
    except XLRDError as e:
        print('Error opening workbook:'+e)
        return None
    
    sheet = book.sheet_by_index(0)
    # Site is always B19 per Evan
    siteName = sheet.cell_value(rowx=18, colx=1)
    
    if verbose:
        print ('Site name: '+siteName)

    if siteName not in sites:
        # Not in list yet - add a tuple
        siteData = SiteData(logFile, minDate=None, maxDate=None, numRecs=0)
        # Open the sheet and grab the data, copying it to the output CSV
        try:
            dataSheet = book.sheet_by_index(1)
            if verbose:
                print('Sheets: ',book.sheet_names())

        except XLRDError as e:
            print('Error getting data sheet for '+logFile+' - Skipping Workbook for "'+siteName+'"')
            return False

        # Switch to data sheet
        sheet = book.sheet_by_index(1)
        
        # Get first line from sheet and analyze
        numColumns = sheet.ncols   # Number of columns
        if sheet.cell_value(rowx=0,colx=0) == u'Date':            
            for rowIndex in range(1, sheet.nrows):    # Iterate through rows
                if verbose:
                    print ('-'*40)
                    print ('Row: %s' % rowIndex)   # Print row number
                for columnIndex in range(0, numColumns):  # Iterate through columns
                    cellValue = sheet.cell(rowIndex, columnIndex)  # Get cell object by row, col
                    cellType = cellValue.ctype
                    
                    # Special case - time is a separate value, but returned as date - skip it since
                    # we don't care about time, only date
                    if (columnIndex == 1 and cellType == 3):
                        continue
                    else:
                        if verbose:
                            print ('Column: [%s] is [%s] : [%s]' % (columnIndex, cellType, cellValue))
                        # Somewhere these numeric values have to be defined, right?
                        # 3 == date per https://pythonhosted.org/xlrd3/cell.html
                        if (cellType == 3):
                            outputCSV.write(str(datetime.datetime(*xlrd.xldate_as_tuple(cellValue.value, book.datemode)))+",")
                        elif (cellType in [1, 2]):   # 1 = text, 2 = number
                            outputCSV.write(str(cellValue.value)+",")
                        else:
                            print ('Unknown value type for [%s,%s] : %s' % (rowIndex, columnIndex, cellType))
        return True
    # print('*WARNING* Duplicate data for site "'+siteName+'" in '+sites{siteName}.filePath)
    return False
        
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
   

if __name__ == "__main__":
   main(sys.argv[1:])
