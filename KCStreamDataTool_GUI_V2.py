# -*- coding: utf-8 -*-
"""
Created on Tue Apr 10 21:25:38 2018
@author: Evan Romasco-Kelly

GUI for KC Stream Data Tool (script written by Mike Kelly)

"""

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import os


class KCStreamDataApp():
    
    def __init__(self):
        self.window = tk.Tk()
        #self.window.configure(background = "SystemAppWorkspace")
        self.window.wm_title("KC Monitoring Data Processor")
        
        self.CreateWidgets()
        
    def CreateWidgets(self):   
        """Called by __init__ to build and position widgets of the KC Stream Data Processor GUI"""
        
        # Configure method for rows and columns of self.window which gives them "weight" and allows them to resize
        self.window.rowconfigure(1, weight=1)
        self.window.rowconfigure(2, weight=1)
        self.window.rowconfigure(3, weight=1)
        self.window.columnconfigure(1, weight=1)
        
        #Create Label Frame
        lbl_Title = ttk.Label(self.window, text = "KC Monitoring Data Formatter", padding = 10)
        lbl_Title.grid(row=1,column=1)
        
        # ---------------------------------------------------------------------        
        # Create Frame for input/output file browse and entry boxes
        Frm_InputOutput = ttk.Frame(self.window, relief=tk.RIDGE, padding=6)
        Frm_InputOutput.grid(row = 2, column = 1, padx=6, sticky=tk.E + tk.W + tk.N + tk.S)
        
        # Text control for where the input files are
        lbl_InputFiles = tk.Label(Frm_InputOutput, text = "Input files")
        lbl_InputFiles.grid(row = 1, column = 1)
        
        self.str_InputFiles = tk.StringVar()        
        self.entry_InputFiles = tk.Entry(Frm_InputOutput, textvariable = self.str_InputFiles)
        self.entry_InputFiles.grid(row = 1, column = 2, padx = 10, ipadx = 3, ipady = 3, sticky = tk.E + tk.W)
        
        # Text control for where the output goes
        lbl_OutputFiles = tk.Label(Frm_InputOutput, text = "Output files")
        lbl_OutputFiles.grid(row = 2, column = 1)
        
        self.str_OutputFiles = tk.StringVar()
        self.entry_OutputFiles = tk.Entry(Frm_InputOutput, textvariable = self.str_OutputFiles)
        self.entry_OutputFiles.grid(row = 2, column = 2, padx = 10, ipadx = 3, ipady = 3,sticky = tk.E + tk.W)
        
        # Buttons to call file browser dialog for input/output directories
        btn_BrowseInputDir = ttk.Button(Frm_InputOutput, text = "Browse", command = self.BtnPress_BrowseInput)
        btn_BrowseInputDir.grid(row = 1, column = 3, pady = 2, ipadx = 5, ipady = 3)
        
        btn_BrowseOutputDir = ttk.Button(Frm_InputOutput, text = "Browse", command = self.BtnPress_BrowseOutput)
        btn_BrowseOutputDir.grid(row = 2, column = 3, pady = 2, ipadx = 5, ipady = 3)
        
        # Row and column configuration:
        Frm_InputOutput.columnconfigure(1, weight = 1)
        Frm_InputOutput.columnconfigure(2, weight = 2)
        Frm_InputOutput.columnconfigure(3, weight = 1)
        
        
        # ---------------------------------------------------------------------
        # Create Choices Frame with temperature, logger, and quit buttons
        Frm_Choices = ttk.Frame(self.window, relief=tk.FLAT, padding=6)
        Frm_Choices.grid(row = 3, column = 1, padx=6, sticky=tk.E + tk.W + tk.N + tk.S)
        
        # Buttons to choose temperature or logger data output
        btn_TemperatureData = ttk.Button(Frm_Choices, text = "Temperature", command = self.BtnPress_Temperature)
        btn_LoggerData = ttk.Button(Frm_Choices, text = "Logger", command = self.BtnPress_Logger)
        
        btn_TemperatureData.grid(row = 1 ,column = 1, pady = 5, ipadx = 7, ipady = 3, sticky=tk.W)
        btn_LoggerData.grid(row = 1, column = 2, pady = 5, ipadx = 7, ipady = 3, sticky=tk.E)
        
        # Button to quit the program
        btn_QuitWin = ttk.Button(Frm_Choices, text = "Quit", command = self.QuitWin)
        btn_QuitWin.grid(row = 2, column = 2, pady = 10, ipadx = 7, ipady = 3, sticky=tk.E)
        
        #Rows and Columns configurations (deals with resizing window)
        Frm_Choices.rowconfigure(1, weight = 1)
        Frm_Choices.rowconfigure(2, weight = 1)
        Frm_Choices.columnconfigure(1, weight = 1)
        Frm_Choices.columnconfigure(2, weight = 1)
        
        # Create the output window
        termf = tk.Frame(self.window) #, height=100, width=500)
        termf.grid(row = 4, column = 1)
        
        wid = termf.winfo_id()


    def BtnPress_Temperature(self):
        """Only called for button to start the mungeStreamData.py script with the option "-t" """
            
        InputFiles = self.str_InputFiles.get()
        OutputFiles = self.str_OutputFiles.get()
        
        if len(InputFiles) == 0:
           messagebox.showerror("Error", "Please choose a folder containing the input files")
           return
       
        if len(OutputFiles) == 0:
           messagebox.showerror("Error", "Please choose a folder to deposit the output files")
           return
        
        option = "-t"
        
        
        print("The temperature button was pressed and will pass the option", option)
        os.system('cmd /k python MungeStreamData.py -i "{}" -o "{}" {}'.format(InputFiles, OutputFiles, option))
    
    def BtnPress_Logger(self):
        """Only called for Logger button to start the mungeStreamData.py script"""
            
        InputFiles = self.str_InputFiles.get()
        OutputFiles = self.str_OutputFiles.get()
        
        if len(InputFiles) == 0:
           messagebox.showerror("Error", "Please choose a folder containing the input files")
           return
       
        if len(OutputFiles) == 0:
           messagebox.showerror("Error", "Please choose a folder to deposit the output files")
           return
        
        self.window.destroy()
        
        print("The logger button was pressed")
        os.system('cmd /k python MungeStreamData.py -i "{}" -o "{}"'.format(InputFiles, OutputFiles))
        
        
    def BtnPress_BrowseInput(self):
        """Calls a file dialog box when the 'browse' button for the input files field is pressed"""
        
        from tkinter.filedialog import askdirectory      
        
        filename = askdirectory()
        
        self.entry_InputFiles.delete(0, tk.END)
        self.entry_InputFiles.insert(0, filename)
        
            
    def BtnPress_BrowseOutput(self):
        """Calls a file dialog box when the 'browse' button for the output files field is pressed"""
        
        from tkinter.filedialog import askdirectory      
        
        filename = askdirectory()
        
        self.entry_OutputFiles.delete(0, tk.END)
        self.entry_OutputFiles.insert(0, filename)
        
    def QuitWin(self):
        """Closes the window when the 'Quit' button is pressed"""
        self.window.destroy()
        

program = KCStreamDataApp()
program.window.mainloop()