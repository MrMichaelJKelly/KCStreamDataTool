# -*- coding: utf-8 -*-
"""
Created on Sun Jul 22 12:21:54 2018

@author: Evan Romasco-Kelly
"""

import re
import os
import csv
import ntpath

verbose = False

# Files to exclude from if present
filesToExclude = ['.dropbox', 'desktop.ini' ]

#Locate files to process
def collectFiles(inputFolder, outputFolder=None):
    filesToRead = []
    # Regular expression to identify files we are interested in processing - for
    
    logFilePattern = re.compile('.*\.csv$')
        
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
    if verbose:
        print(filesToRead)                
    return filesToRead

def SplitDO(file):
    if verbose:
        print("in SplitDO")
    datafile = open(file, 'r')
    reader = csv.reader(datafile)
    T_outputFileName = "Temp_"+str(ntpath.basename(file))
    DO_outputFileName = "DO_"+str(ntpath.basename(file))
    print("Writing file,", str(ntpath.basename(file))+"...")
    
    T_outputPath = os.path.join("C:\\Users\\Evan Romasco-Kelly\\OneDrive\\Documents\\Kooskooskie Commons\\WADOE Reporting\\EIM\\DO and Temp Files", T_outputFileName)
    DO_outputPath = os.path.join("C:\\Users\\Evan Romasco-Kelly\\OneDrive\\Documents\\Kooskooskie Commons\\WADOE Reporting\\EIM\\DO and Temp Files", DO_outputFileName)
    T_outfile = open(T_outputPath, 'w')
    DO_outfile = open(DO_outputPath, 'w')
    T_writer = csv.writer(T_outfile, lineterminator='\n')
    DO_writer = csv.writer(DO_outfile, lineterminator='\n')
    
    count = 1    
    for row in reader:
        if count == 1:
            DO_writer.writerow(row)
            T_writer.writerow(row)
            count += 1
            continue
        elif row[15] == "Dissolved Oxygen":
            DO_writer.writerow(row)
        elif row[15] == "Temperature, water":
            T_writer.writerow(row)
        count += 1
        if verbose:
            print(row)
    
    datafile.close()
    T_outfile.close()
    DO_outfile.close()


def main():
    inputFolder1 = input("Input Folder Path:\n")
    
    filesToProcess = collectFiles(inputFolder1)
    for afile in filesToProcess:
        SplitDO(afile)

main()