* KCStreamDataTool
Tool for munging KC Stream Data 

Mini Spec for Data Massaging

#Current situation
HI-9829 Data is located in a non-organized folder tree with general name of "LOG0XX_#########"
Each file has two sheets
* Sheet 1, "Lot Info" has the measurement information
  * Most importantly, it includes lot names, which are the site names
  * For example, Yelac = YELAC, and Rutzpond = RUTZP
  * Some of the lot names are wrong (e.g. WHISI should be WHIRU)
  * Lot names are located in cell B19
* Sheet 2, "Log data - 1", contains a series of measurements for a given day
  * Sometimes the days are "on top" of each other in the same column
  * Sometimes the file has the data for a single day
  * Sometimes the data has the data for a single day, but for some reason the first several hundred rows are empty
#What I want
1. First, I want the raw data files organized: one file per site per measurement day
  * Named as "SITENAME_YYYY-MM-DD" (e.g. YELAC_2017-10-01)
  * These files should be put in the correct folders (either by measurement days or sites?)
  * _OPEN ISSUE:_ Do I want all the measurements from YELAC together or all the measurements from 10-01-17 together?
  * Then, I want the median measurement for each parameter per site per measurement day (that is to say, I want one value for dissolved oxygen at YELAC for 10-01-17)
      * This means taking the median for a given day
  * Maybe I make third sheet which "summarizes" the data by giving me a median value for the parameters as well as date and time
  * Lastly, I want all of the median values put into my summary/master spreadsheet
*	Each site has its own sheet
*	I want to populate the tables with median values from each date/time and parameter
*	From there, I will prepare the EIM files?
*	Eventually, I think I will need each parameter for each site to be in its own EIM-formatted CSV which we can then upload to DOE

