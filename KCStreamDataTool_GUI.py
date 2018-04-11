# -*- coding: utf-8 -*-
"""
Created on Tue Apr 10 21:25:38 2018
@author: Evan Romasco-Kelly

GUI for KC Stream Data Tool (script written by Mike Kelly)

"""

import tkinter as tk
#import tkFileDialog

def BtnPress(btn_Name):
    print("The {} button was pressed".format(btn_Name))


window = tk.Tk()

lbl_Title = tk.Label(window, text = "Kooskooskie Monitoring Data Processor")
lbl_Title.grid(row=1,column=2)

# Text control for where the input files are
lbl_InputFiles = tk.Label(window, text = "Input files")
lbl_InputFiles.grid(row = 2, column = 1)

entry_InputFiles = tk.Entry(window)
entry_InputFiles.grid(row = 2, column = 2)


# Text control for where the output goes
lbl_OutputFiles = tk.Label(window, text = "Output files")
lbl_OutputFiles.grid(row = 3, column = 1)

entry_OutputFiles = tk.Entry(window)
entry_OutputFiles.grid(row = 3, column = 2)

# Buttons to choose temperature or logger data output
btn_TemperatureData = tk.Button(window, text = "Temperature", command = lambda: BtnPress("Temperature"))
btn_LoggerData = tk.Button(window, text = "Logger", command = lambda: BtnPress("Logger"))

btn_TemperatureData.grid(row = 4,column = 1)
btn_LoggerData.grid(row = 4, column = 3)

root.mainloop()