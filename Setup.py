# -*- coding: utf-8 -*-
"""
Created on Mon Sep 10 16:12:23 2018

@author: Evan Romasco-Kelly
"""

import cx_Freeze
import sys
import os

os.environ['TCL_LIBRARY'] = r'C:\Users\Evan Romasco-Kelly\Anaconda3\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\Evan Romasco-Kelly\Anaconda3\tcl\tk8.6'

base = None

if sys.platform == 'win32':
    base = "Win32GUI"

executables = [cx_Freeze.Executable("KCStreamDataTool_GUI_V2.py", base=base, icon='KC_GUI.ico',
                                    targetName = "KCStreamDataTool.exe", shortcutName = "KC Stream Data Tool")]

cx_Freeze.setup(
        name = "KCStreamDataTool_GUI_V2",
        options = {"build_exe":{"packages":["tkinter",
                                            "xlrd",
                                            "subprocess",
                                            "threading",
                                            "queue",
                                            "time",
                                            "os",
                                            "collections",
                                            "sys",
                                            "datetime",
                                            "dateutil",
                                            "getopt",
                                            "heapq",
                                            "re",
                                            "platform",
                                            "csv",
                                            "collections"],
                    "include_files":["FormatStreamData.py","KC_GUI.ico", "GUI_Welcome_Message.txt"]}},
        version = "1.1",
        description = "Data formatting tool for water quality data collected by Kooskooskie Commons",
        executables = executables
        )