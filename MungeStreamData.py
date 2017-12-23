#!/usr/bin/env python3
#
# Script to read a bunch of data files with measurements from
# streams and consolidate them, standardize format, eliminate
# duplicate data readings, etc.
#
# Mike Kelly - December 2017

import os
import sys
import getopt
import re
import platform
from pathlib import Path
from xlrd import open_workbook, XLRDError

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
                m = re.match( logFilePattern, file)
                if m:
                    # print('Adding '+os.path.join(subdir, file))
                    filesToRead.append(os.path.join(subdir, file))
    return filesToRead

# Process the log files found
def processLogFiles(logFiles):
    for file in logFiles:
        processLogFile(file)

def processLogFile(logFile):
    print('Processing '+logFile)
    try:
        book = open_workbook(logFile)
    except XLRDError as e:
        print('Error opening workbook:'+e)
        return
    
    sheet = book.sheet_by_index(0)
    # Site is always B19 per Evan
    site_name = sheet.cell_value(rowx=18, colx=1)
    
    print ('Site name: '+site_name)
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
   outputFolder = 'ProcessedStreamData'
   inputFolder = '.'

   try:
      opts, args = getopt.getopt(argv,"i:ho:",["input=", "help", "output="])
   except getopt.GetoptError:
      helpMessage()
   for opt, arg in opts:
      if opt == '-h':
         helpMessage()
      elif opt in ("-o", "--output"):
         outputFolder = arg
      elif opt in ("-i", "--input"):
         inputFolder = arg

   if inputFolder == '':
         helpMesssage()

   print('Processing data in "'+ inputFolder+ '"...')
   
   files = collectFiles(inputFolder, outputFolder)
   processLogFiles(files)
   

if __name__ == "__main__":
   main(sys.argv[1:])
