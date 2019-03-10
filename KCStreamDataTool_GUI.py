# -*- coding: utf-8 -*-
"""
Created on Tue Apr 10 21:25:38 2018
@author: Evan Romasco-Kelly

GUI for KC Stream Data Tool (script written by Mike Kelly)

"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os


def BtnPress(btn_Name):
    # Only called for Logger and Temperature Buttons to start the mungeStreamData.py script
    global window, entry_InputFiles, entry_OutputFiles, wid
        
    InputFiles = entry_InputFiles.get()
    OutputFiles = entry_OutputFiles.get()
    
    if len(InputFiles) == 0:
       messagebox.showerror("Error", "Please choose a folder containing the input files")
       return
   
    if len(OutputFiles) == 0:
       messagebox.showerror("Error", "Please choose a folder to deposit the output files")
       return
    
    if btn_Name == "Temperature":
        option = "-t"
    else:
        option = ""
    
    
    print("The {} button was pressed".format(btn_Name))
    os.system('cmd /k python MungeStreamData.py -i "{}" -o "{}" {}'.format(InputFiles, OutputFiles, option))
    
    
def BtnPress_Browse(entry_Name):
    from tkinter.filedialog import askdirectory
    
    global window, entry_InputFiles, entry_OutputFiles
    
    filename = askdirectory()
    if entry_Name == "entry_InputFiles":
        entry_InputFiles.delete(0, END)
        entry_InputFiles.insert(0, filename)
    else:
        entry_OutputFiles.delete(0, END)
        entry_OutputFiles.insert(0, filename)
        

global window, entry_InputFiles, entry_OutputFiles, wid
window = tk.Tk()
window.wm_title("KC Monitoring Data Processor")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
# Input/Output Files Frame
frm_IOFiles = tk.Frame(window, padx = 5, pady = 5, relief = tk.RIDGE)
frm_IOFiles.grid(row = 1, column = 1, sticky = tk.E + tk.W + tk.N + tk.S)

lbl_Title = tk.Label(frm_IOFiles, text = "Kooskooskie Monitoring Data Processor")
lbl_Title.grid(row=1,column=2)

# Text control for where the input files are
lbl_InputFiles = tk.Label(frm_IOFiles, text = "Input files")
lbl_InputFiles.grid(row = 2, column = 1)

entry_InputFiles = tk.Entry(frm_IOFiles)
entry_InputFiles.grid(row = 2, column = 2)


# Text control for where the output goes
lbl_OutputFiles = tk.Label(frm_IOFiles, text = "Output files")
lbl_OutputFiles.grid(row = 3, column = 1)

entry_OutputFiles = tk.Entry(frm_IOFiles)
entry_OutputFiles.grid(row = 3, column = 2)


# Buttons to call file browser dialog for input/output directories
btn_BrowseInputDir = tk.Button(frm_IOFiles, text = "Browse", command = lambda: BtnPress_Browse("entry_InputFiles"))
btn_BrowseInputDir.grid(row = 2, column = 3)

btn_BrowseOutputDir = tk.Button(frm_IOFiles, text = "Browse", command = lambda: BtnPress_Browse("entry_OutputFiles"))
btn_BrowseOutputDir.grid(row = 3, column = 3)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
# Temperature/Logger Output Choice Buttons Frame
frm_OutputChoice = tk.Frame(window, relief = tk.RIDGE)
frm_OutputChoice.grid(row = 2, column = 1, sticky=tk.E + tk.W + tk.N + tk.S)

# Buttons to choose temperature or logger data output
btn_TemperatureData = tk.Button(frm_OutputChoice, text = "Temperature", command = lambda: BtnPress("Temperature"))
btn_LoggerData = tk.Button(frm_OutputChoice, text = "Logger", command = lambda: BtnPress("Logger"))

btn_TemperatureData.grid(row = 1,column = 1, sticky = tk.W)
btn_LoggerData.grid(row = 1, column = 2, sticky = tk.E)

# Create the output window
termf = tk.Frame(frm_OutputChoice, height=100, width=500)
termf.grid(row = 2, column = 2)

wid = termf.winfo_id()

root.mainloop()