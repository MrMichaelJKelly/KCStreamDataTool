# -*- coding: utf-8 -*-
"""
Created on Tue Apr 10 21:25:38 2018
@author: Evan Romasco-Kelly

GUI for KC Stream Data Tool (script written by Mike Kelly)

"""

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import tkinter.scrolledtext as tkst
import subprocess as sbp
import threading as thd
import queue as Queue
import os
from time import sleep

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
        btn_LoggerData.grid(row = 1, column = 2, pady = 5, ipadx = 7, ipady = 3)
        
        #Create checkbutton for user to indicate if they want Ecology EIM-formatted files
        self.DoEOutputOpt = tk.IntVar()
        chkbtn_DoEOutput = tk.Checkbutton(Frm_Choices, text = "Create Ecology EIM-formatted files", 
                                          variable = self.DoEOutputOpt) #, onvalue = "True", offvalue = "False")
        chkbtn_DoEOutput.grid(row = 1, column = 3, pady = 5, ipadx = 7, ipady = 3, sticky=tk.E)

        
        #Rows and Columns configurations (deals with resizing window)
        Frm_Choices.rowconfigure(1, weight = 1)
        Frm_Choices.columnconfigure(1, weight = 1)
        Frm_Choices.columnconfigure(2, weight = 1)
        Frm_Choices.columnconfigure(3, weight = 1)
        
        
        # ---------------------------------------------------------------------
        # Create the output window/Frame
        Frm_Output = ttk.Frame(self.window, relief = tk.FLAT, padding=6)
        Frm_Output.grid(row = 4, column = 1, padx=6, sticky=tk.E + tk.W + tk.N + tk.S)
        
        lbl_Output = tk.Label(Frm_Output, text = "Progress")
        lbl_Output.grid(row = 1, column = 1)
        
        self.txt_Output = tkst.ScrolledText(Frm_Output, wrap = tk.WORD, width  = 50, height = 4)
        self.txt_Output.grid(row = 2, column = 1, ipadx = 5, ipady = 5, padx = 10, pady = 10)
        
#        termf = tk.Frame(self.window) #, height=100, width=500)
#        termf.grid(row = 4, column = 1)
#        
#        wid = termf.winfo_id()
        
        # ---------------------------------------------------------------------
        # Create the quit window button
        Frm_Quit = ttk.Frame(self.window, relief = tk.FLAT, padding = 6)
        Frm_Quit.grid(row=5, column = 1, padx=6, sticky=tk.E + tk.W + tk.N + tk.S)
        
        btn_QuitWin = ttk.Button(Frm_Quit, text = "Quit", command = self.QuitWin)
        btn_QuitWin.grid(row = 1, column = 1, pady = 10, ipadx = 7, ipady = 3, sticky=tk.E)
        
        Frm_Quit.rowconfigure(1, weight = 1)
        Frm_Quit.columnconfigure(1, weight = 1)
        

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
        
        
        if self.DoEOutputOpt == 1:
            print('cmd /k python MungeStreamData.py -i "{}" -o "{}" -t -e'.format(InputFiles, OutputFiles))
        else:
            print('cmd /k python MungeStreamData.py -i "{}" -o "{}" -t'.format(InputFiles, OutputFiles))
       # os.system('cmd /k python MungeStreamData.py -i "{}" -o "{}" {}'.format(InputFiles, OutputFiles, option))
    
    def BtnPress_Logger(self):
        """Only called for Logger button to start a thread in which the MungeStreamData.py script will be run"""
                    
        if len(self.str_InputFiles.get()) == 0:
           messagebox.showerror("Error", "Please choose a folder containing the input files")
           return
       
        if len(self.str_OutputFiles.get()) == 0:
           messagebox.showerror("Error", "Please choose a folder to deposit the output files")
           return
        
        LoggerOutput = thd.Thread(target = self.GetLoggerOutput)
        LoggerOutput.start()

        self.window.update_idletasks()        


    def GetLoggerOutput(self):
        """Starts the MungeStreamData.py script in a thread and dynamically returns standard output to the scrolled text widget"""
        InputFiles = self.str_InputFiles.get()
        OutputFiles = self.str_OutputFiles.get()
        
        if self.DoEOutputOpt.get() == 1:
            DoE_Logger = "-e"
            #print('cmd /k python MungeStreamData.py -i "{}" -o "{}" -e'.format(InputFiles, OutputFiles))
        else:
           DoE_Logger = ""
            #print('cmd /k python MungeStreamData.py -i "{}" -o "{}"'.format(InputFiles, OutputFiles))
        
        myList = ['python', '-u', 'MungeStreamData.py', '-i ', InputFiles, '-o ', OutputFiles, DoE_Logger]
        print(myList)       
            
        proc_Logger = sbp.Popen(['python', '-u', 'MungeStreamData.py', '-i', InputFiles, '-o ', OutputFiles, DoE_Logger],
                                stdout = sbp.PIPE)
        stdout_Queue = Queue.Queue()
        stdout_Reader = AsynchronousFileReader(proc_Logger.stdout, stdout_Queue)
        stdout_Reader.start()
        line = ""
        
        while not stdout_Reader.eof(): 
            while not stdout_Queue.empty():
                line = stdout_Queue.get()
                if line == "<<Done!>>\r\n" or line == b'':
                    #print("breaking #1")
                    break
                print(line.decode())
                #self.txt_Output.insert(tk.INSERT, line.decode()+"\n")
                #self.txt_Output.see("end")
                self.window.update_idletasks()
                
            if line == "<<Done!>>\r\n" or line == b'':
                #print("breaking #2")
                break
            #print("sleeping")
            sleep(0.1) #Sleep a bit before checking the readers            

        print("Exiting CallOutput")
#        self.window.destroy()
#        
#        print("The logger button was pressed")
#        os.system('cmd /k python MungeStreamData.py -i "{}" -o "{}"'.format(InputFiles, OutputFiles))
#        
        
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
        
#    def GetOutput(self):
#        GetOutput = thd.Thread(target = self.CallOutput)
#        GetOutput.start()
#
#        self.window.update_idletasks()        
##        self.window.update_idletasks()
#    
#    def CallOutput(self):
#        print("In CallOutput")
#        
#        proc = sbp.Popen(['python', '-u', 'Subprocess_test_Output.py'], stdout = sbp.PIPE)
#        stdout_Queue = Queue.Queue()
#        stdout_Reader = AsynchronousFileReader(proc.stdout, stdout_Queue)
#        stdout_Reader.start()
#        line = ""
#        
#        while not stdout_Reader.eof(): 
#            while not stdout_Queue.empty():
#                line = stdout_Queue.get()
#                if line == "<<Done!>>\r\n" or line == b'':
#                    #print("breaking #1")
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
#
#        print("Exiting CallOutput")

        
    def QuitWin(self):
        """Closes the window when the 'Quit' button is pressed"""
        self.window.destroy()
        

program = KCStreamDataApp()
program.window.mainloop()