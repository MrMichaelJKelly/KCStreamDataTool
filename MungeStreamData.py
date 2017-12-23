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

# Locate Dropbox folder
# From https://stackoverflow.com/questions/12118162/how-can-i-get-the-dropbox-folder-location-programmatically-in-python
def getDropboxFolderPath():
    try:
        jsonPath = (Path(os.getenv('LOCALAPPDATA'))/'Dropbox'/'info.json').resolve()
    except FileNotFoundError:
        jsonPath = (Path(os.getenv('APPDATA'))/'Dropbox'/'info.json').resolve()
    
    with open(str(jsonPath)) as f:
        j = json.load(f)

    # os.path.join adds trailing slash if not there    
    businessDropboxFolderRoot = os.path.join(Path(j['business']['path']), '')
    print('Looking in Dropbox at', businessDropboxFolderRoot)
    return businessDropboxFolderRoot
    
# Locate files to include in the archive
def collectFiles(businessDropboxFolderRoot, projectName):
    filesToZip = []
    projectRoot = businessDropboxFolderRoot + projectName
    for subdir, dirs, files in os.walk(projectRoot):
        for file in files:
            if file not in filesToExclude:
                # Check if this file matches one of the directories we want to include
                # skip others, e.g. To-From Target
                if len([x for x in dirsToInclude if subdir.find('\\'+x)>0])>0:
                    print('Adding '+os.path.join(subdir, file))
                    filesToZip.append('"'+os.path.join(subdir, file)+'"')
    return filesToZip
        

# Zip up files
# Returns CompletedProcess with output
def sevenzipWindows(files, zipname, password):
    
    # Base zip command with name of archive and password
    cmd = ["7z", "a", "-p{}".format(password), '--', zipname.title()]
    # Append the list of files to add to the ZIP archive
    fd, path = mkstemp()
    # use a context manager to open the file at that path and close it again
    with open(path, 'w') as f:
        f.write('\n'.join(files))

    os.close(fd)
    cmd.append('@'+path)
    print('7Zip execution:\n', cmd)
    return subprocess.run(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, universal_newlines=True)

def helpMessage():
      print('techdna-archive.py -p <project>')
      print('Creates archive for project in Tech DNA Dropbox / Project Archives')
      sys.exit(2)


def main(argv):
   projectName = ''
   
   # Only supporting Windows for now...
   if (platform.system() != 'Windows'):
        print('Sorry, this script is supported only on Windows for now... bug Mike')
        sys.exit(2)
        
   dropboxFolderRoot = getDropboxFolderPath()

   try:
      opts, args = getopt.getopt(argv,"hp:",["project="])
   except getopt.GetoptError:
      helpMessage()
   for opt, arg in opts:
      if opt == '-h':
         helpMessage()
      elif opt in ("-p", "--project"):
         projectName = arg

   print('Archiving "'+projectName+'"...')
   
   files = collectFiles(dropboxFolderRoot, projectName)
   # TO DO - generate password
   SevenZipStatus = sevenzipWindows(files, os.path.join(dropboxFolderRoot, 'Project Archives', projectName + ' Project Archive.zip'), '12345')
   print (SevenZipStatus.stdout)

if __name__ == "__main__":
   main(sys.argv[1:])
