#!/usr/bin/env python3
#
# Script to read a bunch of data files with measurements from
# streams and consolidate them, standardize format, eliminate
# duplicate data readings, etc.
# Two CSV files are output:
# 1 has median values and measurement data rows aggregated across all input files
# The other is in a format for Washington Department of Ecology and matches this template:
# Sample CSV output
# Yellowhawk,<Site>,<Site>,Measurement,NGO,<Start Date (MM/DD/YYYY),Time (HH:MM:SS,24),,,,,,,,,,,,,,,,Water (col 24),Fresh/Surface Water,,,,,,,,,<parameter>,,,,,<median>,<unit>,,,,,,,,,,,<method>
#
# Time is earliest start time for that date
# <method> how it was measured - see methodsDoESummary
# <unit> is a mapping based on parameter (e.g. Percent)
#
# Mike Kelly - December 2017 - January 2018

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
from collections import defaultdict

# Files to exclude from list of found files if present
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

# handle to output CSV files
outputCSVSummary = None     # Data summary by site, with median values
outputCSVDoE = None         # Output for DoE logger data

# Temperature data
outputCSVDoETemperature = None


# Standard data headers - some are in a slightly different format and have to be massaged a bit...
columnHeaders = [ 'Date', 'Time', 'Temp.[C]', 'pH', 'mV [pH]', 'EC[uS/cm]', 'D.O.[%]', 'D.O.[ppm]', 'Turb.FNU', 'Remarks', 'Other' ]

# This list is 1:1 with columnHeaders and shows which columns we should calculate a median for.
# The medians are calculated per site/per date.
calculateMedians = [ False, False, True,      True, True,       True,        True,      True,        True,       False,      False ]

# List of measurements to include in the DoE Summary CSV,
# with value to put in the "Result_Parameter_Name" column for that item
includeInDoESummary = {
    'Temp.[C]' : 'Temperature, water',
    'pH' : 'pH',
    'D.O.[%]' : 'Dissolved Oxygen Percent Saturation',
    'EC[uS/cm]' : 'Electrical Conductivity',
    'Turb.FNU' : 'Turbitity'
}

# Result_Value_Units values corresponding to items in the DoE summary
valueUnitsDoESummary = {
    'Temp.[C]' : 'deg C',
    'pH' : 'pH',
    'D.O.[%]' : '%',
    'EC[uS/cm]' : 'uS/cm',
    'Turb.FNU' : 'FNU'
}

# List of units and methods - each measurment has a list that [0] is the Unit value and [1] is the method value
methodsDoESummary = { 'Temp.[C]' : 'TEMPLOGGER',
                    'pH' : 'PHMETER',
                    'D.O.[%]' : 'DO-OPTICAL',
                    'EC[uS/cm]' : 'CONDMETER',
                    'Turb.FNU' : 'TURBM'
}

# We added handling of temperature data and the DoE summary for temperature data later in the project - so
# some values have Xxxxx and XxxxxTemp - the Xxxx is for the HI-9829 and the xxxxTemp is for the temperature loggers

# Headers for the DoE Output file for Hi-9829 - this is the format of each line in that file
outputCSVDoEHeaders = [
    'Study_ID',
    'Location_ID',
    'Study_Specific_Location_ID',
    'Field_Collection_Type',
    'Field_Collector',
    'Field_Collection_Start_Date',
    'Field_Collection_Start_Time',
    'Field_Collection_End_Date',
    'Field_Collection_End_Time',
    'Field_Collection_Comment',
    'Field_Collection_Area',
    'Field_Collection_Area_Units',
    'Field_Collection_Reference_Point',
    'Field_Collection_Upper_Depth',
    'Field_Collection_Lower_Depth',
    'Field_Collection_Depth_Units',
    'Well_Water_Level_Measuring_Point_or_TOC_ID',
    'Sample_ID',
    'Sample_Field_Replicate_ID',
    'Sample_Replicate_Flag',
    'Sample_Sub_ID',
    'Sample_Composite_Flag',
    'Storm_Event_Qualifier',
    'Sample_Matrix',
    'Sample_Source',
    'Sample_Use',
    'Sample_Collection_Method',
    'Sample_Preparation_Method',
    'Sample_Method_Other',
    'Sample_Taxon_Name',
    'Sample_Taxon_TSN',
    'Sample_Tissue_Type',
    'Sample_Percent_Sorted',
    'Result_Parameter_Name',
    'Result_Parameter_CAS_Number',
    'Lab_Analysis_Date',
    'Lab_Analysis_Date_Accuracy',
    'Lab_Analysis_Time',
    'Result_Value',
    'Result_Value_Units',
    'Result_Reporting_Limit',
    'Result_Reporting_Limit_Type',
    'Result_Detection_Limit',
    'Result_Detection_Limit_Type',
    'Result_Data_Qualifier',
    'Fraction_Analyzed',
    'Field_Filtered_Flag',
    'Result_Basis',
    'Digestion_Method',
    'Water_Level_Accuracy',
    'Result_Method',
    'Result_Comment',
    'Result_Additional_Comment',
    'Result_Lab_Replicate_ID',
    'Result_Lab_Name',
    'Result_Validation_Level',
    'Result_Taxon_Name',
    'Result_Taxon_TSN',
    'Result_Taxon_Unidentified_Species',
    'Result_Taxon_Life_Stage'
]

# Headers for Temperature DoE output file
outputCSVDoETemperatureHeaders = [
    'Study_ID',
    'Instrument_ID',    # If Yelmo, YelRu, YelPR = Onset HOBO U26-001, otherwise Onset HOBO U22-001
    'Location_ID',
    'Study-Specific_Location_ID',
    'Field_Collection_Type',
    'Field_Collector',
    'Field_Collection_Reference_Point',
    'Field_Collection_Depth',
    'Field_Collection_Depth_Units',
    'Matrix',
    'Source',
    'Start_Date',
    'Start_Time',
    'End_Date',
    'End_Time',
    'Parameter_Name',    # DO = "Disolved Oxygen", Temperature = "Temperature, water"
    'Result_Value',
    'Result_Unit',          # DO = mg/L, Temperature = deg C
    'Result_Data_Qualifier',
    'Result_Method',
    'Comment',
    'Groundwater_Result_Accuracy',
    'Groundwater_Level_Measuring_Point_ID',
]


# Locate files to process - if doTemperature is True, doing temperature
# files - otherwise LOG files
def collectFiles(inputFolder, outputFolder, doTemp):
    global verbose
    
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
    # particular site.  The list has the values for each date.  The timestamps are als
    # a per-date list but just have the first time we encountered on that date - it is
    # for the DoE Logger summary (per Evan, first time is OK)
    def __init__(self, site, item):
        self.siteName = site
        self.itemName = item
        self.medianFinders = {}
        self.timestamps = {}
    
    def recordValue(self, dt, tm, val):
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
            # Per Evan - OK to just remember the first timestamp for a day - this is needed for
            # DoE Summary
            self.timestamps[dt] = tm
        # Record a new value for a site we've already seen - the Median Finder accumulates
        # these to eventually find the median.
        self.medianFinders[dt].addNum(val)
        if verbose:
            print('recordValue: recorded %f for %s at %s' % (val, dt, tm))
    
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

# A list of temperature values for a particular site/item by date
# Designed to be put in a list indexed by site and item.
# Will record both DO and temperature if both are available - that's itemName
class SiteItemTempMeasurements(object):

    # Create a holder for a list of median values for a particular measurement for a
    # particular site.  The list has the values for each date.  The timestamps are als
    # a per-date list but just have the first time we encountered on that date - it is
    # for the DoE Logger summary (per Evan, first time is OK)
    def __init__(self, site, item):
        self.siteName = site
        self.itemName = item
        self.values = defaultdict(defaultdict)      # dictionary of dictionaries indexed by date and time
    
    def recordValue(self, dt, tm, val):
        global verbose
        self.values[dt][tm] = val
        if verbose:
            print('recordValue: recorded %f for %s at %s' % (val, dt, tm))


# This list consists of SiteItemMeasurements objects that record values per-site, per-date for each item marked
# above as needing a median.  
class MedianCollector(object):
    # List of SiteItemMeasurements values
    siteMeasurementValues = {}
    
    def addMeasurement(self, site, dt, tm, item, val):
        global verbose
        if verbose:
            print('Recording %s as %f' % (item, val))
        if site not in self.siteMeasurementValues:      # first time we are seeing this site
            self.siteMeasurementValues[site] = {}
        if item not in self.siteMeasurementValues[site]:    # first time for this measurement
            # Don't yet have a tracker for this item for this site - add it
            self.siteMeasurementValues[site][item] = SiteItemMeasurements(site, item)
        # Now record the value for this item on this date at this site
        self.siteMeasurementValues[site][item].recordValue(dt, tm, val)

    # Emit the summary files per site with median values
    # if isForDoE - we are emitting the summary for the DoE
    def emitMedianValuesCSV(self, outputCSVSummaryFile, isForDoE):
        for site, siteCollection in self.siteMeasurementValues.items():
            for item, itemCollection in siteCollection.items():
                for dt, medianValue in itemCollection.calcMedians().items():
                    if not isForDoE:
                        outputCSVSummaryFile.write('%s,"%s",%s,%f\n' % (site, item, dt, medianValue))
                    else:
                        # DoE Summary is only for certain measurements and has a completely different format
                        # Get the time to report for this date
                        tm = itemCollection.timestamps[dt]
                        if item in includeInDoESummary.keys():
                            # <StudyID>,<Site>,<Site>,Measurement,NGO,<Start Date (MM/DD/YYYY),Time (HH:MM:SS,24),,,,,,,,,,,,,,,,Water (col 24),Fresh/Surface Water,,,,,,,,,<parameter>,,,,,<median>,<unit>,,,,,,,,,,,<method>
                            outputCSVSummaryFile.write('Yellowhawk,"%s","%s",Measurement,NGO,"%s","%s",,,,,,,,,,,,,,,,"Water","Fresh/Surface Water",,,,,,,,,"%s",,,,,%f,"%s",,,,,,,,,,,"%s"\n' % (site, site,dt,tm,includeInDoESummary[item],medianValue,valueUnitsDoESummary[item],methodsDoESummary[item]))

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
# This routine reads both formats and emits a per-site CSV file with this format:
#
# Site,"Date Time, GMT-07:00","DO conc, mg/L","Temp, DegF","Source File"
#
# As well as a per-site format for the WA State DoE
#
def processTemperatureFiles(temperatureFiles, logFile, outputFolder):

    global outputCSVSummary
    
    ret = True      # optimistic
    
    siteDataFiles = {}       # indexed by site, gives handle of file
    
    # Write header for all-up summary that aggregates all sites.
    outputCSVSummary.write('"Site","Date","Time (GMT-07:00)","DO conc (mg/L)","Temp (DegF)","RawDataFile"\n')
    
    try:    
        # Process each data (temperature) file
        for file in temperatureFiles:
            logFile.write("=== %s ===\n" % file)
            if not processTemperatureFile(file, logFile, outputFolder, siteDataFiles):
                ret = False

    finally:
        logFile.close()
        # Close each per-site DoE summary file created
        for siteDataFile in siteDataFiles:
                siteDataFiles[siteDataFile].close()


    return ret

# Mapping of temperature site names in data files to output site names
def mapTemperatureSiteName(siteName):
    temperatureSiteMap = {
        'Caldwell_Mouth' : 'CALDM',
        'Caldwell_Source' : 'CALDS',
        'Cottonwood_Plaza_Way' : 'COTPR',
        'Cottonwood Plaza Way' : 'COTPR',
        'Garrison___Source' : 'GARRS',
        'Garrison _ Source' : 'GARRS',
        'GarrisonMouth_11-5-15_QAQC' : 'GARMO',
        'Lassiter_Source_Air' : 'LASCB_Air',
        'Russell_Creek_Plaza_Way' : 'RUSPR',
        'Rutzer\'s_Spring' : 'RUTZP',
        'Stone_Mouth_11-5-15_QAQC' : 'STOMO',
        'Stone_Source' : 'STONS',
        'Stone_Source_Air' : 'STONS_Air',
        'Whitney_Spring_Creek_Rutzer_Dr' : 'WHISP',
        'Whitney_Spring_Creek_Shives_Drive' : 'WHIRU',
        'Whitney Spring Creek Rutzer Dr' : 'WHISP',
        'Whitney Spring Creek Shives Drive' : 'WHIRU',
        'Yellowhawk_mouth_air' : 'YELMO_Air',
        'Yellowhawk_Old_Milton_Hiway' : 'YELMO',
        'Yellowhawk_Plaza_Way' : 'YELPR',
        'Yellowhawk_Rupars' : 'YELRU',
        'Yellowhawk_Source_11-5-15_QAQC' : 'YELAC',
		'Butcher_Mouth' : 'BUTMO',
		'Butcher_source' : 'BUTSO',
		'Butcher_Source' : 'BUTSO',
		'Caldwell_Mouth' : 'CALDM',
		'Garrison___Mouth' : 'GARMO',
		'Garrison_Source' : 'GARRS',
		'Lassiter_Mouth' : 'LASOM',
		'Lassiter_Spring' : 'LASCB',
		'Lincoln_mouth' : 'LINMO',
		'Lincoln_mouth_air' : 'LINMO_Air',
		'Lincoln_source' : 'LINSO',
		'Titus_Mouth' : 'TITMO',
		'Titus_mouth_air' : 'TITMO_Air',
		'Yellowhawk_@_Rupar_(2)' : 'YELRU',
		'YellowHawk_@_Rupar_11-5-15_QAQC' : 'YELRU',
		'Yellowhawk_source' : 'YELAC',
		'YellowhawkCreekPlazaWy_11-5-15_QAQC' : 'YELPR'        
    }
    return temperatureSiteMap.get(siteName.replace(' ','_'), None)


# Process one raw data temperature file 
def processTemperatureFile(rawDataFile, logFile, outputFolder, siteDataFiles):
    
    global sites, outputCSVSummary
    global DoEOutputOption
    nRows = 0           # Number rows written to output
    ret = True
    
    print('\nProcessing '+rawDataFile)
    try:
        with open(rawDataFile) as csvfile:
            datarows = csv.reader(csvfile)
            for row in datarows:
                if nRows == 0:      # Site name - after "Plot Name: " on first row.  Sigh.
                                    # Too bad whoever did this had no $*#*$*$ idea what a
                                    # well-formed CSV file is supposed to look like.
                    # Some of the CSV files are in UTF-8 which means they have a Unicode signature
                    # Just look for the :
                    siteNamePos = row[0].find(':')
                    if siteNamePos == -1:
                        siteName = row[0]   # No :?
                    else:
                        siteName = row[0][(siteNamePos+2):].rstrip()
                    # Some of the CSV files have a trailing " - remove it
                    if len(siteName) > 1 and siteName[-1] == '"':
                        siteName = siteName[:-1]
                    # Use the mapping list to standardize sitenames
                    newSiteName = mapTemperatureSiteName(siteName)
                    print ('Site name in data file {} => {}'.format(siteName,newSiteName))
                    if newSiteName is None:
                        print('No mapping for site name, skipping file')
                        logFile.write('No mapping for site name "{}", skipping file\n'.format(siteName))
                        ret = False
                    else:
                        siteName = newSiteName
                else:
                    numColumns = len(row)
                    if numColumns >= 7:
                        # Determine which flavor of format we've got based on CSV header
                        # If we have both - emit two rows, one per measurement.
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
                        # Have we seen this site before, i.e. do we have a file for it?
                        if siteName not in siteDataFiles:
                            if DoEOutputOption:                            
                                # First time we've seen this site - create a file and emit the header
                                siteTemperatureFilePath = os.path.join(outputFolder, siteName + "_Temperature_DoE.csv")
                                siteDataFiles[siteName] = open(siteTemperatureFilePath, 'w')
                                # Write the CSV header row for the 
                                # per-site DoE Summary
                                for item in outputCSVDoETemperatureHeaders:
                                    siteDataFiles[siteName].write(item+',')
                                siteDataFiles[siteName].write('\n')
                        # Handle some data mappings and split out date and time
                        specialSites = [ "YELMO" , "YELRU" , "YELPR" ]
                        if siteName in specialSites:
                            instrumentID = "Onset HOBO U26-001"
                        else:
                            instrumentID = "Onset HOBO U22-001"
                        # Split up date and time
                        try:
                            # Parse the string in the second column that contains date and time into a Python
                            # DateTime object that we can then manipulate
                            dttime = parse(row[1])
                            dt = dttime.strftime("%m-%d-%Y")
                            tm = dttime.strftime("%H:%M:%S")
                        except ValueError:
                            dt = ""
                            tm = ""

                        # Write to the all-up summary that isn't for the DoE
                        outputCSVSummary.write('{},{},{},{},{},{}\n'.format(siteName, dt, tm, temp, do, rawDataFile))
                        
                        # Write to DoE Summary file - different format, one line per measurement for DO and temp
                        # If DO is present in input data, emit rows for both DO and temp
                        if DoEOutputOption:
                            if hasDO:
                                # Yellowhawk,<Instrument>,<Site>,<Site>,Measurement,NGO,,,,Water,Fresh/Surface Water,<Start Date (MM/DD/YYYY),Time (HH:MM:SS,24),,,<parameter>,<val>,<unit>,<method>
                                siteDataFiles[siteName].write('Yellowhawk,"%s","%s","%s",Measurement,NGO,,,,"Water","Fresh/Surface Water","%s","%s",,,"%s","%s","%s",,"DO-OPTICAL"\n' % (instrumentID, siteName, siteName, dt,tm,"Dissolved Oxygen",do,"mg/L"))
                            #Temp
                            siteDataFiles[siteName].write(    'Yellowhawk,"%s","%s","%s",Measurement,NGO,,,,"Water","Fresh/Surface Water","%s","%s",,,"%s","%s","%s",,"TEMPLOGGER"\n' % (instrumentID, siteName, siteName, dt,tm,"Temperature, water",temp,"deg F"))
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

#
# HI-9829 Data FILES
#
# Process the HI-9829 files found
def processLogFiles(outputLogFile, logFiles):
    global outputCSVSummary
    global outputCSVDoE
    global DoEOutputOption
    
    ret = True      # optimistic
    
    skip_these = (
        "WARNING *** OLE2 inconsistency",
        )
    try:        
        xlrdLogFile = XlrdLogFileFilter(outputLogFile, skip_these)
        
        # Write the CSV header row
        outputCSVSummary.write('Site, RawDataFile,')
        for colName in columnHeaders:
            outputCSVSummary.write(colName+',')
        outputCSVSummary.write('\n')

        medianCollector = MedianCollector()       
        
        # Process each data (log) file
        for file in logFiles:
            outputLogFile.write("=== %s ===\n" % file)
            if not processLogFile(file, xlrdLogFile, medianCollector):
                outputLogFile.write('Error processing %s\n' % file)
                ret = False
    except Exception as e:
        outputLogFile.write("Error - %s\n", str(e))
        ret = False 
        
    # Emit the median values for each measurement to the CSV
    outputCSVSummary.write('\n\nMEDIAN VALUES\nSite,Measurement,Date,Median\n')
    medianCollector.emitMedianValuesCSV(outputCSVSummary,False)
    
    # Write the DoE summary CSV
    if DoEOutputOption:
        for item in outputCSVDoEHeaders:
            outputCSVDoE.write(item+',')
        outputCSVDoE.write('\n')    
        medianCollector.emitMedianValuesCSV(outputCSVDoE,True)

    return ret

# Process one raw data file (a/k/a LogFile which is confusing, since it conflicts
# with XLRD's use of LogFile as a output of errors, warnings, etc.)
# the second parameter here is used for XLRD's log  messages
 
def processLogFile(rawDataFile, xlrdLog, medianCollector):
    
    global sites, outputCSVSummary
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
               'LASMO' : 'LASOM',
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
                    outputCSVSummary.write(',')
                    continue
                else:
                    cellValue = sheet.cell(rowIndex, columnIndex)  # Get cell object by row, col
                    cellType = cellValue.ctype
                    
                    # Prefix each row with the site name of the data and the
                    # file name it came from
                    if (columnIndex == 0):
                        outputCSVSummary.write(siteName+','+rawDataFile+',')
                        
                    if verbose:
                        print ('Column: [%s] is [%s] : [%s]' % (columnIndex, cellType, cellValue))
                        
                    # Somewhere these numeric values have to be defined, right?
                    # 3 == date per https://pythonhosted.org/xlrd3/cell.html - but there are two
                    # in the data, a date and a time.  0 is the date, 1 is the time.  Sigh.
                    if (cellType == 3):
                        if (columnIndex == 0):      # Date
                            # Date
                            year, month, day, hour, minute, second = xldate.xldate_as_tuple(cellValue.value, book.datemode)
                            strDate = '%4d-%02d-%02d' % (year, month, day)
                            outputCSVSummary.write(strDate)
                            d = datetime.date(year,month,day)
                            if (d < earliestDateSeen):
                                earliestDateSeen = d
                            if (d > latestDateSeen):
                                latestDateSeen = d
                        else:  # Only other date value in input is the Time stamp
                            # Just emit time as is.  Remember since we need to add it
                            # to the median finder so we can emit the timestamp in the
                            # DoE Summary.
                            year, month, day, hour, minute, second = xldate.xldate_as_tuple(cellValue.value, book.datemode)
                            strTime = '%02d:%02d:%02d' % (hour, minute, second)
                            outputCSVSummary.write(strTime)
                    elif (cellType in [1, 2]):   # 1 = text, 2 = number
                            # Other column - e.g. ph, Turb.FNU, etc.
                            outputCSVSummary.write(str(cellValue.value))
                            # Do we need to accumulate values for this for median calculation?
                            # Note some measurements have '-----' instead of 0 for missing values
                            # so catch that here by checking only for numeric values
                            if cellType == 1:
                                measurementValue = 0
                            else:
                                measurementValue = cellValue.value
                            if calculateMedians[columnIndex]:
                                medianCollector.addMeasurement(siteName, strDate, strTime, columnHeaders[columnIndex], measurementValue)
                    else:
                        xlrdLog.write('%s: Unknown value type for [%s,%s] : %s\n' % (rawDataFile, rowIndex, columnIndex, cellType))
                    if (nCols < nColsToWrite):
                        outputCSVSummary.write(',')        # append , except after last column value                    
                        
            # After emitting all columns, terminate the line in the CSV file
            outputCSVSummary.write('\n')       # Terminate line
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
        
 
def helpMessage():
      print('Usage:')
      print('MungeStreamData.py [-t] [-h] [-v] [-e] [-o <outputFolder>] -i <inputFolder>')
      print('Processes all data files under <inputFolder>; default is current directory')
      print('Output goes to specified output folder, default is ProcessedStreamData')
      print('Optional parameters:')
      print('    -t   - process temperature data files, not logger files.  Without -t, logger files are processed.')
      print('    -e   - output WA Department of Ecology EIM-formatted .csv files')
      print('    -h   - print this help message')
      print('    -v   - verbose output (for debugging the tool)')
      sys.exit(2)


def main(argv):
   
   # Only supporting Windows for now...
    if (platform.system() != 'Windows'):
        print('Sorry, this script is supported only on Windows for now... bug Mike')
        sys.exit(2)

    global verbose
    global outputCSVSummary
    global outputCSVDoE
    global sites
    global DoEOutputOption
   
   # Defaults for output folder, input folder and whether we are processing logger or
   # temperature files
    outputFolder = 'ProcessedStreamData'
    inputFolder = '.'
    doTemperature = False
<<<<<<< HEAD
    DoEOutputOption = False
=======
    doDoE = False
>>>>>>> ccdd2b62ec85c3f6fc097ccd6f664b5f44711890

    # Arguments passed on command line are in the "argv" list
    try:
<<<<<<< HEAD
        opts, args = getopt.getopt(argv,"vhi:o:te",["verbose", "help", "input=", "help", "output=", "temp", "ecology"])
=======
        opts, args = getopt.getopt(argv,"vhi:o:te",["verbose", "help", "input=", "help", "output=", "temp","dodoe"])
>>>>>>> ccdd2b62ec85c3f6fc097ccd6f664b5f44711890
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
<<<<<<< HEAD
        elif opt in ("-e", "--ecology"):
            DoEOutputOption = True
=======
        elif opt in ("-e", "--dodoe"):
            doDoE = True
>>>>>>> ccdd2b62ec85c3f6fc097ccd6f664b5f44711890

    if inputFolder == '' or not os.path.isdir(inputFolder):
        print(inputFolder+' is not a folder containing data files.')
        helpMessage()

    # Open up log file        
    try:
        logPath = os.path.join(outputFolder, "LogFile.txt")
        outputLogFile = open(logPath, 'w')
    except IOError as e:
        print('Error opening '+logPath,': '+ str(e))
        exit(-1)

    if doTemperature:
        # For temperature data - we just emit per-site DoE summary files, not
        # an aggregated file as we do for loggers
        outputSummaryPath = os.path.join(outputFolder, 'TemperatureData.CSV')

        try:
            outputCSVSummary = open(outputSummaryPath, 'w')
        except IOError as e:
            print('Error opening '+outputSummaryPath,': '+ str(e))
            helpMessage()

        print('Processing Temperature file data in "'+ inputFolder+ '"...')
        print('Writing to:\n'+outputSummaryPath+'\nand per-site DoE files named Xxxxx_Temperature_DoE.csv\n')
    else:
        # We emit two output files - Summary  which is an aggregated summary of all the data files
        # we read, and DoESummary which is for input to the DoE site in a format they prescribe.
        outputSummaryPath = os.path.join(outputFolder, 'StreamData.CSV')
        if DoEOutputOption:
            outputDoESummaryPath = os.path.join(outputFolder, 'HI-9829_For_DoE.CSV')
        
            try:
                outputCSVDoE = open(outputDoESummaryPath, 'w')
            except IOError as e:
                print('Error opening '+outputDoESummaryPath,': '+ str(e))
                helpMessage()

        try:
            outputCSVSummary = open(outputSummaryPath, 'w')
        except IOError as e:
            print('Error opening '+outputSummaryPath,': '+ str(e))
            helpMessage()
    
        print('Processing LOG file data in "'+ inputFolder+ '"...')
        print('Writing to "'+ outputSummaryPath+ '"...')
   
    # Get list of files to process - either temperature or logger files
    files = collectFiles(inputFolder, outputFolder, doTemperature)
    
    if doTemperature:
        processTemperatureFiles(files, outputLogFile, outputFolder)
    else:
        if not processLogFiles(outputLogFile, files):
            print("Something went wrong, check the error log\n")
        
    outputCSVSummary.close()
    outputLogFile.close()

    print('<<Done!>>')
    
    # Dump out collected per-site data
    if not doTemperature:
        for site in sites:
            print('For "' + site +'"')
            for item in sites[site]:
                print('\tData from %s to %s' % (str(item.minDate), str(item.maxDate)))
                print('\t%d records from: %s' % (item.numRecs, item.filePath))
            print('-'*50)
   

if __name__ == "__main__":
   main(sys.argv[1:])
