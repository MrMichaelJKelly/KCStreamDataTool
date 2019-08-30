# KCStreamDataTool - Tool for munging KC Stream Data 
Changed by Evan

# Mini Spec for Data Massaging

## Current situation
HI-9829 Data is located in a non-organized folder tree with general name of "LOG0XX_#########"
Each file has two sheets
- Sheet 1, "Lot Info" has the measurement information
  - Most importantly, it includes lot names, which are the site names
  - For example, Yelac = YELAC, and Rutzpond = RUTZP
  - Some of the lot names are wrong (e.g. WHISI should be WHIRU)
  - Lot names are located in cell B19
- Sheet 2, "Log data - 1", contains a series of measurements for a given day
  - Sometimes the days are "on top" of each other in the same column
  - Sometimes the file has the data for a single day
  - Sometimes the data has the data for a single day, but for some reason the first several hundred rows are empty
# What I want
1. First, I want the raw data files organized: one file per site per measurement day
  - Named as "SITENAME_YYYY-MM-DD" (e.g. YELAC_2017-10-01)
  - These files should be put in the correct folders (either by measurement days or sites?)
  - _OPEN ISSUE:_ Do I want all the measurements from YELAC together or all the measurements from 10-01-17 together?
  - Then, I want the median measurement for each parameter per site per measurement day (that is to say, I want one value for dissolved oxygen at YELAC for 10-01-17)
      - This means taking the median for a given day
  - Maybe I make third sheet which "summarizes" the data by giving me a median value for the parameters as well as date and time
  - Lastly, I want all of the median values put into my summary/master spreadsheet
Each site has its own sheet
 - I want to populate the tables with median values from each date/time and parameter
_OPEN ISSUE:_ From there, I will prepare the EIM files?
Eventually, I think I will need each parameter for each site to be in its own EIM-formatted CSV which we can then upload to DOE

# Pre-requisites
Install Python 3 from https://www.python.org/downloads/ (make sure you get Python 3.x not 2.x)
Once installed, install the two packages this solution depends on (included in this repo):

Make sure this both are installed for Python 3 on your machine:
    
	C:\Users\mikek\Dropbox (Personal)\src\KCStreamDataTool>py -V
	Python 3.6.4
	
	C:\Users\mikek\Dropbox (Personal)\src\KCStreamDataTool>py -m pip install xlrd-1.1.0-py2.py3-none-any.whl
	Processing c:\users\mikek\dropbox (personal)\src\kcstreamdatatool\xlrd-1.1.0-py2.py3-none-any.whl
	Installing collected packages: xlrd
	Successfully installed xlrd-1.1.0
	
	C:\Users\mikek\Dropbox (Personal)\src\KCStreamDataTool>py -m pip install python_dateutil-2.6.1-py2.py3-none-any.whl
	Processing c:\users\mikek\dropbox (personal)\src\kcstreamdatatool\python_dateutil-2.6.1-py2.py3-none-any.whl
	Collecting six>=1.5 (from python-dateutil==2.6.1)
	  Downloading six-1.11.0-py2.py3-none-any.whl
	Installing collected packages: six, python-dateutil
	Successfully installed python-dateutil-2.6.1 six-1.11.0

# Command line

-i xxxxx    Input - read files in xxxxx directory and below (for temperature data, it is looking for .CSV files
			in this directory - for Log file data, it is looking for .xls files in this directory and below.
			NOTE: *xls* files, not *xlsx* files.

-o xxxxx	Put output data in directory xxxx.  This is where the summary CSV will be created.

-t			Summarize temperature data.  Default is to summarize Logger data, so if -t isn't supplied, the tool
			will look for .xls files from loggers and summarize those.  -t changes it to look for .CSV files
			containing temperature data and summarize those.

-v			Verbose.  For debugging, print a lot of info about what the tool is doing

-h			Help - print an explanation of these command line options


# Debugging Notes

08/30/2019 - changed the HOBO logger site mapping so that if a file comes in with a name that is not in the mapping, it is assumed that the name is already correct, so it uses the file name in the data file.

