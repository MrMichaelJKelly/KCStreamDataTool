# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 15:08:40 2018

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

def change2023Dates(file, datesChange):
    if verbose:
        print("in Change2023Dates")
    datafile = open(file, 'r')
    reader = csv.reader(datafile)
    outputFileName = ntpath.basename(file)
    print("Writing file,", str(outputFileName)+"...")
    
    outputPath = os.path.join("C:\\Users\\Evan Romasco-Kelly\\OneDrive\\Documents\\Kooskooskie Commons\\WADOE Reporting\\EIM\\DO and Temp Files", outputFileName)
    outfile = open(outputPath, 'w')
    writer = csv.writer(outfile, lineterminator='\n')
    
    count = 1    
    for row in reader:
        if count == 1:
            row = changeTimeSeriesHeaders(row)
        if row[11] in datesChange:
            #olddate = row[11]
            row[11] = datesChange[str(row[11])]
            #print("In", outputFileName, "and Date", olddate, "changed to", row[11])
        if row[12] in datesChange:
            #olddate = row[12]
            row[12] = datesChange[str(row[12])]
            #print("In", outputFileName, "and Date", olddate, "changed to", row[12])
        if row[16] == "":
            count += 1
            continue    #Skip writing the row in the result value column is blank
        writer.writerow(row)
        count += 1
        if verbose:
            print(row)
    
    datafile.close()
    outfile.close()
    
def changeTimeSeriesHeaders(headerList):
    headerList = ['Study_ID','Instrument_ID','Location_ID','Study-Specific_Location_ID',
    'Field_Collection_Type','Field_Collector','Field_Collection_Reference_Point',
    'Field_Collection_Depth','Field_Collection_Depth_Units','Matrix','Source',
    'Start_Date','Start_Time','End_Date','End_Time','Parameter_Name','Result_Value',
    'Result_Unit','Result_Data_Qualifier','Result_Method','Comment','Groundwater_Result_Accuracy',
    'Groundwater_Level_Measuring_Point_ID']
    return headerList
                
def createDateDict():
    dateDict = {'11/3/2023':'9/30/2017'}
    new = 1
    for x in range(4,25):
        oldstr = '11/'+str(x)+'/2023'
        newstr = '10/'+str(new)+'/2017'
        dateDict.update({oldstr:newstr})
        new += 1
    if verbose:
        print("Created Date Dictionary")
    return dateDict

def main():
    inputFolder1 = input("Input Folder Path:\n")
#    outputFolder1 = input("Output Folder Path:\n")
    dateChangeDict = createDateDict()
    
    filesToProcess = collectFiles(inputFolder1)
    for afile in filesToProcess:
        change2023Dates(afile, dateChangeDict)

main()