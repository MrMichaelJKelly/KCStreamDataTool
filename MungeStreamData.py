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
import platform
from pathlib import Path



# Files to exclude from the Dropbox list if present
filesToExclude = ['.dropbox', 'desktop.ini' ]

# Directories to include in Zip
# If any one missing, it is skipped
dirsToInclude = ['Artifacts', 'Surveyor', 'To-From Client', 'StaticAnalysis']

# Locate files to process
def collectFiles(inputFolder, outputFolder):
    filesToRead = []
    for subdir, dirs, files in os.walk(inputFolder):
        for file in files:
            if file not in filesToExclude:
                # Check if this file matches one of the directories we want to include
                # skip others, e.g. To-From Target
                if len([x for x in dirsToInclude if subdir.find('\\'+x)>0])>0:
                    print('Adding '+os.path.join(subdir, file))
                    filesToRead.append('"'+os.path.join(subdir, file)+'"')
    return filesToRead
        

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
      opts, args = getopt.getopt(argv,"iho:",["input=", "help", "output="])
   except getopt.GetoptError:
      helpMessage()
   for opt, arg in opts:
      if opt == '-h':
         helpMessage()
      elif opt in ("-o", "--output:"):
         outputFolder = arg
      elif opt in ("-i", "--input:"):
         inputFolder = arg

   if inputFolder == '':
         helpMesssage()

   print('Processing data in "'+ inputFolder+ '"...')
   
   files = collectFiles(inputFolder, outputFolder)
   print(files)

if __name__ == "__main__":
   main(sys.argv[1:])
