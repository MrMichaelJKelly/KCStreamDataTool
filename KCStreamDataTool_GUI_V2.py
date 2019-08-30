# -*- coding: utf-8 -*-
"""
Created on Tue Apr 10 21:25:38 2018
@author: Evan Romasco-Kelly

GUI for KC Stream Data Tool (script written by Mike Kelly)

09/23/2018: Version 1.0 created, note: "Logger" refers to HI-9829 data and "Temperature" refers to HOBO Datalogger data
08/30/2019: Version 1.1, changed the HOBO logger site mapping in FormatStreamData so that if a file comes in with a name that is not in the mapping, it is assumed that the name is already correct, so it uses the file name in the data file.

"""

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import tkinter.scrolledtext as tkst
import threading as thd
import FormatStreamData
import os
import queue


class KCStreamDataApp():
    
    def __init__(self):
        self.window = tk.Tk()
        #self.window.configure(background = "SystemAppWorkspace")
        self.window.wm_title("KC Monitoring Data Formatter")
        self.window.iconbitmap("KC_GUI.ico")
        
        self.Verbosity = True
        
        self.CreateWidgets()
        
    def CreateWidgets(self):   
        """Called by __init__ to build and position widgets of the KC Stream Data Formatter GUI"""
        
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
        Frm_InputOutput = ttk.LabelFrame(self.window, relief=tk.RIDGE, padding=6, text = "Choose Input/Output Folders")
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
        # Create Choices Frame with temperature, logger
        Frm_Choices = ttk.LabelFrame(self.window, relief=tk.FLAT, padding=6, text = "Choose Output Options")
        Frm_Choices.grid(row = 3, column = 1, padx=6, pady = 10, sticky=tk.E + tk.W + tk.N + tk.S)
        
        # Buttons to choose temperature or logger data output
        
        # Initializing variable which indicates whether the program will format HOBO temperature data or HI9829 water quality data
        # Default value is 0, meaning program will default to HI-9829 Logger Data
        self.HOBOorHI9829 = tk.IntVar()
        
        radiobtn_LoggerData = ttk.Radiobutton(Frm_Choices, text = "HI-9829 Data", variable = self.HOBOorHI9829, value = 0)
        radiobtn_TemperatureData = ttk.Radiobutton(Frm_Choices, text = "HOBO Data", variable = self.HOBOorHI9829, value = 1)
        
        radiobtn_LoggerData.grid(row = 1, column = 1, pady = 5, ipadx = 7, ipady = 3, sticky=tk.W)
        radiobtn_TemperatureData.grid(row = 1 ,column = 2, pady = 5, ipadx = 7, ipady = 3, sticky=tk.W)
        
        #Create checkbutton for user to indicate if they want Ecology EIM-formatted files
        self.DoEOutputOpt = tk.IntVar()
        chkbtn_DoEOutput = ttk.Checkbutton(Frm_Choices, text = "Create Ecology EIM-formatted files", 
                                          variable = self.DoEOutputOpt) #, onvalue = "True", offvalue = "False")
        chkbtn_DoEOutput.grid(row = 1, column = 3, pady = 5, ipadx = 7, ipady = 3, sticky=tk.E)

        
        #Rows and Columns configurations (deals with resizing window)
        Frm_Choices.rowconfigure(1, weight = 1)
        Frm_Choices.columnconfigure(1, weight = 1)
        Frm_Choices.columnconfigure(2, weight = 1)
        Frm_Choices.columnconfigure(3, weight = 1)
        
        
        # ---------------------------------------------------------------------
        # Create the output window/Frame
        Frm_Output = ttk.LabelFrame(self.window, relief = tk.FLAT, padding=6, text = "Progress Messages")
        Frm_Output.grid(row = 4, column = 1, padx=6, sticky=tk.E + tk.W + tk.N + tk.S)
        
        # Use Tkinter Scrolled Text widget as output message window, start by inputting welcome message
        # from text file
        self.txt_Output = tkst.ScrolledText(Frm_Output, wrap = tk.WORD, width  = 70, height = 8, font = ('Calibri',12))
        self.txt_Output.grid(row = 2, column = 1, ipadx = 10, ipady = 10, padx = 10, pady = 10)
        
        msg_Welcome = open("GUI_Welcome_Message.txt", "r")
        for aline in msg_Welcome:
            self.txt_Output.insert(tk.INSERT, aline)
        msg_Welcome.close()
        
        Frm_Output.rowconfigure(1, weight = 1)
        Frm_Output.columnconfigure(1, weight = 1)
        Frm_Output.columnconfigure(2, weight = 1)


        # ---------------------------------------------------------------------
        # Create the quit, run, and 'see formatted files' frame and buttons buttons
        Frm_RunQuit = ttk.Frame(self.window, relief = tk.FLAT, padding = 6)
        Frm_RunQuit.grid(row=5, column = 1, padx=6, sticky=tk.E + tk.W + tk.N + tk.S)
                
        btn_Run = ttk.Button(Frm_RunQuit, text = "Run", command = self.BtnPress_Run)
        btn_QuitWin = ttk.Button(Frm_RunQuit, text = "Quit", command = self.QuitWin)
        btn_SeeFormattedFiles = ttk.Button(Frm_RunQuit, text = "See Formatted Files", command = self.BtnPress_SeeFormattedFiles)
        
        btn_QuitWin.grid(row = 1, column = 1, pady = 10, ipadx = 7, ipady = 3, sticky=tk.W)
        btn_SeeFormattedFiles.grid(row = 1, column = 2, pady = 10, ipadx = 7, ipady = 3)
        btn_Run.grid(row = 1, column = 3, pady = 10, ipadx = 7, ipady = 3, sticky=tk.E)
        
        
        Frm_RunQuit.rowconfigure(1, weight = 1)
        Frm_RunQuit.columnconfigure(1, weight = 1)
        Frm_RunQuit.columnconfigure(2, weight = 1)
        Frm_RunQuit.columnconfigure(3, weight = 1)
    
    
    def BtnPress_Run(self):
        """"""
                    
        if len(self.str_InputFiles.get()) == 0:
           messagebox.showerror("Error", "Please choose a folder containing the input files")
           return
       
        if len(self.str_OutputFiles.get()) == 0:
           messagebox.showerror("Error", "Please choose a folder to deposit the output files")
           return
        
        InputFiles = self.str_InputFiles.get()
        OutputFiles = self.str_OutputFiles.get()
        
        if self.HOBOorHI9829.get() == 1:
            doTemperature = True
        else:
           doTemperature = False        
        
        if self.DoEOutputOpt.get() == 1:
            DoE_Temperature = True
        else:
           DoE_Temperature = False
        
        try:
            
            StatusQ = queue.Queue()
            
            self.StatusUpdate("<< Working on it... >>", ClearText = True)
            self.LoggerOutput = thd.Thread(target = FormatStreamData.FormatStreamData(OutputFiles, InputFiles, doTemperature, DoE_Temperature, self.Verbosity, StatusQ))
            self.LoggerOutput.daemon = True
            self.LoggerOutput.start()
            
            # Creating queue for status updates from FormatStreamData to be placed which can then be read by GUI
            while True:
                self.window.update_idletasks()
                # This will block the GUI thread from running until there is something to take from the Queue
                try:
                    item = str(StatusQ.get(block = True, timeout = 1))
                    print("popped off the queue %s" % item)
                    self.StatusUpdate(item)
                    if item == FormatStreamData.DONE_MESSAGE:
                        break
                    
                except queue.Empty:
                    pass
            
            print("Done with the queue")
            self.window.update_idletasks()
        except Exception as e:
            self.StatusUpdate("\n"+str(e))
        
        self.window.update_idletasks()
    
    
    def StatusUpdate(self, StatusString, ClearText=False):
        """Given status strings (e.g. from the FormatStreamData thread),
            update the GUI progress window"""
        print("in status update")
        # Clear the textbox if needed
        if ClearText:
            self.txt_Output.delete(1.0, tk.END)
            
        self.txt_Output.insert(tk.INSERT, str(StatusString)+"\n")
        self.txt_Output.see("end")      # Keep the scrolled text window scrolled to the most recent output
        self.window.update_idletasks()        
        
        
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
    
    
    def BtnPress_SeeFormattedFiles(self):
        """Opens the Windows file explorer to the user-selected output folder directory"""
        
        OutputFilesPath = self.entry_OutputFiles.get()
        os.startfile(OutputFilesPath)
        
        
    def QuitWin(self):
        """Closes the window when the 'Quit' button is pressed"""
        self.window.quit()
        quit()
        

program = KCStreamDataApp()
program.window.mainloop()