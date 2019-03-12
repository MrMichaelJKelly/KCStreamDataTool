# -*- coding: utf-8 -*-
"""
Created on Tue Apr 10 21:25:38 2018
@author: Evan Romasco-Kelly

GUI for KC Stream Data Tool (script written by Mike Kelly)

09/23/2018: Version 1.0 created, note: "Logger" refers to HI-9829 data and "Temperature" refers to HOBO Datalogger data

"""

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import tkinter.scrolledtext as tkst
import subprocess as sbp
import threading as thd
import queue as Queue
from time import sleep
import FormatStreamData

class AsynchronousFileReader(thd.Thread):
    '''
    Helper class to implement asynchronous reading of a file
    in a separate thread. Pushes read lines on a queue to
    be consumed in another thread.
    
    Class written by Stefaan Lippens, http://stefaanlippens.net/python-asynchronous-subprocess-pipe-reading/
    '''

    def __init__(self, fd, queue):
        assert isinstance(queue, Queue.Queue)
        assert callable(fd.readline)
        thd.Thread.__init__(self)
        self._fd = fd
        self._queue = queue

    def run(self):
        '''The body of the thread: read lines and put them on the queue.'''
        for line in iter(self._fd.readline, ''):
            self._queue.put(line)

    def eof(self):
        '''Check whether there is no more content to expect.'''
        return not self.is_alive() and self._queue.empty()


class KCStreamDataApp():
    
    def __init__(self):
        self.window = tk.Tk()
        #self.window.configure(background = "SystemAppWorkspace")
        self.window.wm_title("KC Monitoring Data Processor")
        self.window.iconbitmap("KC_GUI.ico")
        
        self.Verbosity = False
        
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
        # Create Choices Frame with temperature, logger, and quit buttons
        Frm_Choices = ttk.LabelFrame(self.window, relief=tk.FLAT, padding=6, text = "Choose Output Options")
        Frm_Choices.grid(row = 3, column = 1, padx=6, pady = 10, sticky=tk.E + tk.W + tk.N + tk.S)
        
        # Buttons to choose temperature or logger data output
        
#        btn_TemperatureData = ttk.Button(Frm_Choices, text = "HOBO Data", command = self.BtnPress_Temperature)
#        btn_LoggerData = ttk.Button(Frm_Choices, text = "HI-9829 Data", command = self.BtnPress_Logger)
#        
#        btn_TemperatureData.grid(row = 1 ,column = 1, pady = 5, ipadx = 7, ipady = 3, sticky=tk.W)
#        btn_LoggerData.grid(row = 1, column = 2, pady = 5, ipadx = 7, ipady = 3)
        
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
        # Create the run and quit window buttons
        Frm_RunQuit = ttk.Frame(self.window, relief = tk.FLAT, padding = 6)
        Frm_RunQuit.grid(row=5, column = 1, padx=6, sticky=tk.E + tk.W + tk.N + tk.S)
                
        btn_Run = ttk.Button(Frm_RunQuit, text = "Run", command = self.BtnPress_Run)
        btn_QuitWin = ttk.Button(Frm_RunQuit, text = "Quit", command = self.QuitWin)
        
        btn_Run.grid(row = 1, column = 2, pady = 10, ipadx = 7, ipady = 3, sticky=tk.E)
        btn_QuitWin.grid(row = 1, column = 1, pady = 10, ipadx = 7, ipady = 3, sticky=tk.W)
        
        
        Frm_RunQuit.rowconfigure(1, weight = 1)
        Frm_RunQuit.columnconfigure(1, weight = 1)
        Frm_RunQuit.columnconfigure(2, weight = 1)
        

#    def BtnPress_Temperature(self):
#        """Only called for button to start the mungeStreamData.py script with the option "-t" """
#        
#        # Checking to make sure the user has provided input/output file paths
#        if len(self.str_InputFiles.get()) == 0:
#           messagebox.showerror("Error", "Please choose a folder containing the input files")
#           return
#       
#        if len(self.str_OutputFiles.get()) == 0:
#           messagebox.showerror("Error", "Please choose a folder to deposit the output files")
#           return
#                
#        InputFiles = self.str_InputFiles.get()
#        OutputFiles = self.str_OutputFiles.get()
#        
#        if self.DoEOutputOpt.get() == 1:
#            DoE_Temperature = True
#        else:
#           DoE_Temperature = False
#        
#        # Start a thread of execution which calls the function that runs the script while allowing
#        # GUI mainloop to continue
#        self.TemperatureOutput = thd.Thread(target = FormatStreamData.FormatStreamData(OutputFiles, InputFiles, True, DoE_Temperature, self.Verbosity))
#        self.TemperatureOutput.daemon = True
#        self.TemperatureOutput.start()
#
#        self.window.update_idletasks()  
#    
#    
#    def GetTemperatureOutput(self):
#        """Starts the MungeStreamData.py script in a thread (to process temperature logger data)
#        and dynamically returns standard output to the scrolled text widget"""
#        
#        self.txt_Output.delete(1.0, tk.END)
#        
#        InputFiles = self.str_InputFiles.get()
#        OutputFiles = self.str_OutputFiles.get()
#        
#        if self.DoEOutputOpt.get() == 1:
#            DoE_Temperature = True
#        else:
#           DoE_Temperature = False
#        
#        try:
#            self.txt_Output.insert(tk.INSERT, "<< Working on it... >>"+"\n")
#            self.txt_Output.insert(tk.INSERT, FormatStreamData.FormatStreamData(OutputFiles, InputFiles, True, DoE_Temperature, Verbose=False)+"\n")
#            self.txt_Output.see("end")      # Keep the scrolled text window scrolled to the most recent output
#            self.window.update_idletasks()
#        except e as Exception:
#            self.txt_Output.insert(tk.INSERT, str(e)+"\n")
#            self.txt_Output.see("end")      # Keep the scrolled text window scrolled to the most recent output
#            self.window.update_idletasks()
 
        
# Commenting out this code because we are changing the GUI from calling a subprocess to calling a function
#        # Use the subprocess module to run the other script in the thread started by the Btn_Press,
#        # passing the input file path, the output file path, and the state of the DoE Output checkbutton
#        # Also, set the standard output of the MungeStreamData.py script to a pipe which can be read
#        # by the GUI. Furthermore, the "-u" option means the script will be run unbuffered, which makes
#        # it possible to read its output continuously in the GUI
#        proc_Temperature = sbp.Popen(['python', '-u', 'MungeStreamData.py', '-i', InputFiles, '-o', OutputFiles, '-t', DoE_Temperature],
#                                stdout = sbp.PIPE)
#        # Create a queue for the standard output and read from it (this code from Stefan Lippens, see above)
#        stdout_Queue = Queue.Queue()
#        stdout_Reader = AsynchronousFileReader(proc_Temperature.stdout, stdout_Queue)
#        stdout_Reader.start()
#        line = ""
#        
#        # Check the readers on two while conditions so that script output is read continuously until
#        # it finishes.
#        while not stdout_Reader.eof(): 
#            while not stdout_Queue.empty():
#                line = stdout_Queue.get()
#                # The End of File catch doesn't work from Lippens' code for some reason, so this
#                # is a hard-coded method to catch the end of the file and break the while loop
#                if line == "<<Done!>>\r\n" or line == b'':
#                    break
#                # Insert script output into scrolled text widget for user to see. Decode method used
#                # because script output comes as a byte-array with weird characters added
#                self.txt_Output.insert(tk.INSERT, line.decode()+"\n")
#                self.txt_Output.see("end")      # Keep the scrolled text window scrolled to the most recent output
#                self.window.update_idletasks()
#                
#            if line == "<<Done!>>\r\n" or line == b'':
#                #print("breaking #2")
#                break
#            #print("sleeping")
#            sleep(0.1) #Sleep a bit before checking the readers            

        print("Exiting CallOutput")
    
    
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
            self.LoggerOutput = thd.Thread(target = FormatStreamData.FormatStreamData(OutputFiles, InputFiles, doTemperature, DoE_Temperature, self.Verbosity, self.StatusUpdate))
            self.LoggerOutput.daemon = True
            self.LoggerOutput.start()
            self.StatusUpdate("<< Working on it... >>", ClearText = True)
        except Exception as e:
            self.StatusUpdate("\n"+str(e))
        
        self.window.update_idletasks()   
    
    
    def StatusUpdate(self, StatusString, ClearText=False):
        """Given status strings (e.g. from the FormatStreamData thread),
            update the GUI progress window"""
        
        # Clear the textbox if needed
        if ClearText:
            self.txt_Output.delete(1.0, tk.END)
            
        self.txt_Output.insert(tk.INSERT, str(StatusString)+"\n")
        self.txt_Output.see("end")      # Keep the scrolled text window scrolled to the most recent output
        self.window.update_idletasks()
    
    
#    def BtnPress_Logger(self):
#        """Only called for Logger button to start a thread in which the MungeStreamData.py script will be run"""
#                    
#        if len(self.str_InputFiles.get()) == 0:
#           messagebox.showerror("Error", "Please choose a folder containing the input files")
#           return
#       
#        if len(self.str_OutputFiles.get()) == 0:
#           messagebox.showerror("Error", "Please choose a folder to deposit the output files")
#           return
#        
#        InputFiles = self.str_InputFiles.get()
#        OutputFiles = self.str_OutputFiles.get()
#        
#        if self.DoEOutputOpt.get() == 1:
#            DoE_Temperature = True
#        else:
#           DoE_Temperature = False
#        
#        try:
#            self.LoggerOutput = thd.Thread(target = FormatStreamData.FormatStreamData(OutputFiles, InputFiles, False, DoE_Temperature, self.Verbosity))
#            self.LoggerOutput.daemon = True
#            self.LoggerOutput.start()
#        
#        self.window.update_idletasks()        
#
#
#    def GetLoggerOutput(self):
#        """Starts the MungeStreamData.py script in a thread (to process HI-9829 data) and dynamically returns standard output to the scrolled text widget"""
#        print("In GetLoggerOutput")
#        self.txt_Output.delete(1.0, tk.END)
#        
#        InputFiles = self.str_InputFiles.get()
#        OutputFiles = self.str_OutputFiles.get()
#        
#        if self.DoEOutputOpt.get() == 1:
#            DoE_Temperature = True
#        else:
#           DoE_Temperature = False
#        
#        try:
#            self.txt_Output.insert(tk.INSERT, "<< Working on it... >>"+"\n")
#            Finished = FormatStreamData.FormatStreamData(OutputFiles, InputFiles, False, DoE_Temperature, Verbose=False)
#            self.txt_Output.insert(tk.INSERT, Finished)+"\n")
#            self.txt_Output.see("end")      # Keep the scrolled text window scrolled to the most recent output
#            self.window.update_idletasks()
#        except e as Exception:
#            self.txt_Output.insert(tk.INSERT, str(e)+"\n")
#            self.txt_Output.see("end")      # Keep the scrolled text window scrolled to the most recent output
#            self.window.update_idletasks()
          
        
        # Commenting out this code because we are changing the GUI from calling a subprocess to calling a function
#        proc_Logger = sbp.Popen(['python', '-u', 'MungeStreamData.py', '-i', InputFiles, '-o', OutputFiles, DoE_Logger],
#                                stdout = sbp.PIPE)
#        stdout_Queue = Queue.Queue()
#        stdout_Reader = AsynchronousFileReader(proc_Logger.stdout, stdout_Queue)
#        stdout_Reader.start()
#        line = ""
#        
#        while not stdout_Reader.eof(): 
#            while not stdout_Queue.empty():
#                line = stdout_Queue.get()
#                if line == "<<Done!>>\r\n" or line == b'':
#                    break
#                self.txt_Output.insert(tk.INSERT, line.decode()+"\n")
#                self.txt_Output.see("end")
#                self.window.update_idletasks()
#                
#            if line == "<<Done!>>\r\n" or line == b'':
#                #print("breaking #2")
#                break
#            #print("sleeping")
#            sleep(0.1) #Sleep a bit before checking the readers
        
        
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
        self.window.quit()
        quit()
        

program = KCStreamDataApp()
program.window.mainloop()