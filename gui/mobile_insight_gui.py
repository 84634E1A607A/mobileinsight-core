#!/usr/bin/python3

"""
Python GUI for MobileInsight
Author: Moustafa Alzantot
Date : Feb 26, 2016
Converted to PyQt6 by Assistant
"""

import sys
import os
from pathlib import Path
from threading import Thread
from random import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import xml.dom.minidom
import xml.etree.ElementTree as ET

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QTableWidget, QTableWidgetItem, 
                             QTreeWidget, QTreeWidgetItem, QLabel, QSlider, QDialog, 
                             QDialogButtonBox, QFileDialog, QMessageBox, QInputDialog,
                             QCheckBox, QListWidget, QListWidgetItem, QProgressDialog, QToolBar, 
                             QStatusBar, QMenuBar, QSplitter, QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QEvent
from PyQt6.QtGui import QAction, QIcon, QPixmap, QFont, QMovie, QCloseEvent

from mobile_insight.analyzer import LogAnalyzer
from mobile_insight.monitor.dm_collector.dm_endec.dm_log_packet import DMLogPacket

# Get the directory containing this script for relative resource paths
GUI_DIR = Path(__file__).parent
ICONS_DIR = GUI_DIR / "icons"


class ResultEvent:
    def __init__(self, data: List[Dict[str, Any]]) -> None:
        self.data = data


class ProgressDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        layout = QVBoxLayout()
        
        # Create a loading animation - using a simple label for now
        self.label = QLabel("Loading...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Try to load a GIF if available
        try:
            movie = QMovie("icons/loading.gif")
            if movie.isValid():
                self.label.setMovie(movie)
                movie.start()
        except:
            # Fallback to text
            self.label.setText("Loading...")
        
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.resize(200, 100)


class TimeWindowDialog(QDialog):
    def __init__(self, parent, start_time, end_time):
        super().__init__(parent)
        self.setWindowTitle("Time Window")
        
        layout = QVBoxLayout()
        
        self.start_label = QLabel("...")
        self.end_label = QLabel("...")
        self.window_label = QLabel("\t to \t")
        
        font = QFont()
        font.setBold(True)
        self.start_label.setFont(font)
        self.end_label.setFont(font)
        
        font_italic = QFont()
        font_italic.setItalic(True)
        self.window_label.setFont(font_italic)
        
        label_layout = QHBoxLayout()
        label_layout.addWidget(self.start_label)
        label_layout.addWidget(self.window_label)
        label_layout.addWidget(self.end_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                     QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start: "))
        self.start_slider = QSlider(Qt.Orientation.Horizontal)
        self.start_slider.setRange(0, 100)
        self.start_slider.setValue(0)
        self.start_slider.setMinimumWidth(250)
        start_layout.addWidget(self.start_slider)
        self.start_slider.valueChanged.connect(self.start_slider_update)
        
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("End: "))
        self.end_slider = QSlider(Qt.Orientation.Horizontal)
        self.end_slider.setRange(0, 100)
        self.end_slider.setValue(100)
        self.end_slider.setMinimumWidth(250)
        end_layout.addWidget(self.end_slider)
        self.end_slider.valueChanged.connect(self.end_slider_update)
        
        self.start_time = start_time
        self.cur_end = end_time
        self.cur_start = self.start_time
        self.unit_seconds = (end_time - start_time).total_seconds() / 100.0
        
        self.updateUI()
        
        layout.addLayout(label_layout)
        layout.addLayout(start_layout)
        layout.addLayout(end_layout)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def start_slider_update(self, value):
        delta_seconds = value * self.unit_seconds
        self.cur_start = self.start_time + timedelta(seconds=int(delta_seconds))
        self.updateUI()
        
    def end_slider_update(self, value):
        delta_seconds = value * self.unit_seconds
        self.cur_end = self.start_time + timedelta(seconds=int(delta_seconds))
        self.updateUI()
        
    def updateUI(self):
        self.start_label.setText(str(self.cur_start))
        self.end_label.setText(str(self.cur_end))


class MyMCD(QDialog):
    def __init__(self, parent, message, caption, choices=[]):
        super().__init__(parent)
        self.setWindowTitle(caption)
        
        layout = QVBoxLayout()
        
        self.message_label = QLabel(message)
        self.list_widget = QListWidget()
        
        for choice in choices:
            item = QListWidgetItem(choice)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
        
        self.select_all_checkbox = QCheckBox('Select all')
        self.select_all_checkbox.stateChanged.connect(self.toggle_all)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                     QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(self.message_label)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.select_all_checkbox)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        self.resize(400, 300)
        
    def GetSelections(self):
        selections = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                selections.append(i)
        return selections
        
    def toggle_all(self, state):
        check_state = Qt.CheckState.Checked if state == 2 else Qt.CheckState.Unchecked
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                item.setCheckState(check_state)


class WindowClass(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.min_time = datetime.strptime("3000 Jan 1", '%Y %b %d')
        self.max_time = datetime.strptime("1900 Jan 1", '%Y %b %d')
        self.selectedTypes = None  # Message Filters
        self.progressDialog = None
        self.basicGUI()

    def basicGUI(self):

        self._log_analyzer = LogAnalyzer(self.OnReadComplete)
        
        # Menu Bar
        menubar = self.menuBar()
        if menubar:
            file_menu = menubar.addMenu('File')
            edit_menu = menubar.addMenu('Edit')

            open_action = QAction('Open', self)
            open_action.setShortcut('Ctrl+O')
            open_action.triggered.connect(self.Open)
            if file_menu:
                file_menu.addAction(open_action)

            exit_action = QAction('Exit', self)
            exit_action.setShortcut('Ctrl+Q')
            exit_action.triggered.connect(self.close)
            if file_menu:
                file_menu.addAction(exit_action)

        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        # Helper function to create icons
        def create_icon(path):
            try:
                return QIcon(path)
            except:
                return QIcon()  # Empty icon as fallback

        open_action = QAction(create_icon("/usr/local/share/mobileinsight/icons/open.png"), "Open", self)
        open_action.triggered.connect(self.Open)
        self.toolbar.addAction(open_action)
        
        self.toolbar.addSeparator()
        
        filter_action = QAction(create_icon("/usr/local/share/mobileinsight/icons/filter.png"), "Filter", self)
        filter_action.triggered.connect(self.OnFilter)
        self.toolbar.addAction(filter_action)
        
        self.toolbar.addSeparator()
        
        search_action = QAction(create_icon("/usr/local/share/mobileinsight/icons/search.png"), "Search", self)
        search_action.triggered.connect(self.OnSearch)
        self.toolbar.addAction(search_action)
        
        self.toolbar.addSeparator()
        
        time_action = QAction(create_icon("/usr/local/share/mobileinsight/icons/time.png"), "Time Window", self)
        time_action.triggered.connect(self.OnTime)
        self.toolbar.addAction(time_action)
        
        self.toolbar.addSeparator()
        
        reset_action = QAction(create_icon("/usr/local/share/mobileinsight/icons/reset.png"), "Reset", self)
        reset_action.triggered.connect(self.OnReset)
        self.toolbar.addAction(reset_action)
        
        self.toolbar.addSeparator()
        
        about_action = QAction(create_icon("/usr/local/share/mobileinsight/icons/about.png"), "About", self)
        about_action.triggered.connect(self.OnAbout)
        self.toolbar.addAction(about_action)

        # Main Panel
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Grid (Table) for log entries
        self.grid = QTableWidget()
        self.grid.setColumnCount(2)
        self.grid.setHorizontalHeaderLabels(["Timestamp", "Type ID"])
        self.grid.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.grid.cellClicked.connect(self.OnGridSelect)
        
        # Left panel for details
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        self.status_text = QLabel(
            "Welcome to MobileInsight 6.0 beta!\n\nMobileInsight is a Python 3 package for mobile network monitoring and analysis on the end device.")
        self.status_text.setWordWrap(True)
        
        self.details_text = QTreeWidget()
        self.details_text.setHeaderLabel("Details")
        
        left_layout.addWidget(self.status_text, 1)
        left_layout.addWidget(self.details_text, 3)
        
        # Add widgets to splitter
        splitter.addWidget(self.grid)
        splitter.addWidget(left_panel)
        splitter.setSizes([600, 400])  # Initial sizes
        
        main_layout.addWidget(splitter)
        
        # Set column widths
        self.grid.setColumnWidth(0, 200)
        self.grid.setColumnWidth(1, 300)
        
        # Status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Window properties
        self.setWindowTitle("MobileInsight")
        self.resize(1200, 800)
        self.show()

        self.data = None

        # Set up custom result handling
        self.result_timer = QTimer()
        self.result_timer.timeout.connect(self.check_results)
        self.result_timer.start(100)  # Check every 100ms
        self.pending_result = None

    def check_results(self):
        if self.pending_result is not None:
            self.OnResult(self.pending_result)
            self.pending_result = None

    def OnResult(self, event):
        if self.progressDialog:
            self.progressDialog.close()
            self.progressDialog = None

        data = event.data if hasattr(event, 'data') else event
        if data:
            self.statusbar.showMessage(f"Read {len(data)} logs")
            self.data = data
            self.data_view = self.data
            self.SetupGrid()

    def Open(self):
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self,
            "Open Log file",
            "",
            "log files (*.mi2log);;All files (*.*)")
        
        if file_paths:
            print(f'Selected {file_paths}')
            try:
                self.grid.clearContents()
                self.grid.setRowCount(0)

                t = Thread(target=self.openFile, args=(file_paths, self.selectedTypes))
                self.progressDialog = ProgressDialog(self)
                t.start()
                self.progressDialog.exec()

                if len(file_paths) == 1:
                    self.setWindowTitle(file_paths[0])
                else:
                    self.setWindowTitle(f"Multiple files in {os.path.dirname(file_paths[0])}")

            except Exception as e:
                print(f"Error while opening file: {e}")

    def OnFilter(self):
        types = list(self._log_analyzer.supported_types)
        checkboxDialog = MyMCD(self, "Filter", "", types)
        if checkboxDialog.exec() == QDialog.DialogCode.Accepted:
            selections = checkboxDialog.GetSelections()
            self.selectedTypes = [types[x] for x in selections]
            if self.data:
                self.data_view = [x for x in self.data if x["TypeID"] in self.selectedTypes]
                self.SetupGrid()

    def OnTime(self):
        timewindowDialog = TimeWindowDialog(self, self.min_time, self.max_time)
        if timewindowDialog.exec() == QDialog.DialogCode.Accepted:
            select_start = timewindowDialog.cur_start
            select_end = timewindowDialog.cur_end
            self.data_view = [
                x for x in self.data_view if datetime.strptime(
                    x["Timestamp"],
                    '%Y-%m-%d  %H:%M:%S.%f') >= select_start and datetime.strptime(
                    x["Timestamp"],
                    '%Y-%m-%d  %H:%M:%S.%f') <= select_end]
            self.SetupGrid()

    def OnReset(self):
        if self.data:
            self.data_view = self.data
            self.SetupGrid()

    def openFile(self, Paths, selectedTypes):
        self._log_analyzer.AnalyzeFile(Paths, selectedTypes)

    def OnSearch(self):
        text, ok = QInputDialog.getText(self, "Search", "Search for:")
        if ok and text:
            self.data_view = [x for x in self.data_view if text in x["Payload"]]
            self.SetupGrid()

    def OnAbout(self):
        about_text = (
                'MobileInsight GUI\n\n\n' +
                'Copyright (c) 2014-2016 MobileInsight Team\n\n' +
                'Developers:\n    Moustafa Alzantot,\n' +
                '    Priyanka Avinash Kachare,\n' +
                '    Michael Ivan,\n' +
                '    Yuanjie Li')
        QMessageBox.information(self, "About MobileInsight GUI", about_text)

    def OnGridSelect(self, row, column):
        if row < len(self.data_view):
            self.status_text.setText(
                f"Time Stamp : {self.data_view[row]['Timestamp']}    Type : {self.data_view[row]['TypeID']}")
            
            self.content = {}
            r = ET.fromstring(str(self.data_view[row]["Payload"]))
            print(r.tag)
            for child in r:
                k = child.get("key")
                if child.get("type")=="list" and len(child)==0:
                    self.content[k]={}
                elif child.get("type") == "list" and child[0].tag == "list":
                    list_content = self.parse_list(child, k)
                    self.content[k] = list_content
                elif child.get("type") == "list" and child[0].tag == "msg":  # xml from wireshark
                    list_content = self.parse_msg(child)
                    self.content[k] = list_content
                elif child.get("type")=="dict":
                    self.content[k]=self.parse_dict(child)
                else:
                    self.content[k] = child.text
                    
            self.details_text.clear()
            root = QTreeWidgetItem(self.details_text)
            root.setText(0, 'payload')
            self.create_tree(self.content, root)
            self.details_text.expandAll()

    def parse_list(self, listroot, attrib_key):
        '''
        convert list from .xml to standard dict
        :param listroot:
        :param attrib_key:
        :return: dict
        '''
        list_content = {}
        if(len(listroot)==0):
            return None
        listroot = listroot[0];  # <pair key="CA Combos" type="list">   <list>
        i = 0
        for xml_list in listroot:
            if xml_list.tag == "item" and xml_list.get("type") == "dict":  # The only subclass of list is dict
                dist_content = self.parse_dict(xml_list)
                if(xml_list.get("key")==None):
                    list_content[attrib_key + "[" + str(i) + "]"] = dist_content 
                    i += 1
                else:
                    list_content[xml_list.get("key")]=dist_content 
        return list_content

    def parse_dict(self, dictroot):
        '''
        convert dict from .xml to standard dict
        :param dictroot:
        :return:
        '''
        dictroot = dictroot[0]  # <item type="dict">  <dict>
        dict_content = {}
        for d in dictroot:
            k = d.get("key")
            if (d.get("type") == "list"):  # list in dist
                list_content = self.parse_list(d, k)
                dict_content[k] = list_content
            elif (d.get("type")=="dict"):
                list_content = self.parse_dict(d)
                dict_content[k] = list_content
            else:
                dict_content[k] = d.text;  # key-value
        return dict_content

    def split_key_value(self,str):
        '''
        e.g. "a:b"->"a","b"
        :param str:
        :return:
        '''
        start=str.find(":")
        if(start!=-1):
            key=str[0:start]
            val=str[start+1:]
            return key ,val
        else:
            return str,"none"
    def parse_msg(self, msgroot):
        '''
        parse xml file which is conveyed by wireshark
        :param msgroot:
        :return:
        '''
        proto = msgroot.findall(".//proto")
        dict_msg = {}
        skip_context=["geninfo","frame","user_dlt"]#proto which is useless
        for p in proto:
            if (p.get("hide") != "yes" and p.get("name") not in skip_context):
                dict_msg.update(self.parse_msg_field(p))
            else:
                continue
        return dict_msg

    def parse_msg_field(self, msgroot):
        msg_dict={}
        #skip_context=["geninfo","frame","user_dlt"]
        for field in msgroot:
            if (field.get("hide") == "yes"):
                continue
            elif len(field) != 0 and field.get("showname")!=None:
                k=field.get("showname")
                k,_=self.split_key_value(k)
                val_dict = self.parse_msg_field(field)
                if len(val_dict)==0:
                    msg_dict[k]="skip"
                else:
                    msg_dict[k]=val_dict
            elif len(field)!=0:
                msg_dict.update(self.parse_msg_field(field))
            else:
                dict_msg = field.get("showname")
                if dict_msg !=None:
                    k, v = self.split_key_value(dict_msg)
                    msg_dict[k] = v
        return msg_dict

    def create_tree(self, payload_dict, root):
        for k, v in payload_dict.items():
            if isinstance(v, dict):
                subroot = QTreeWidgetItem(root)
                subroot.setText(0, str(k))
                self.create_tree(v, subroot)
            else:
                if v != "skip":
                    item = QTreeWidgetItem(root)
                    item.setText(0, f"{k}:{v}")
                else:
                    item = QTreeWidgetItem(root)
                    item.setText(0, str(k))

    def closeEvent(self, a0):
        if a0:
            a0.accept()

    def OnReadComplete(self):
        # Instead of using wx events, we'll use a simple variable
        self.pending_result = ResultEvent(self._log_analyzer.msg_logs)

    def SetupGrid(self):
        self.min_time = datetime.strptime("3000 Jan 1", '%Y %b %d')
        self.max_time = datetime.strptime("1900 Jan 1", '%Y %b %d')

        n = len(self.data_view)
        
        # Set the number of rows
        self.grid.setRowCount(n)
        
        # Clear existing content
        self.grid.clearContents()
        
        # Set headers
        self.grid.setHorizontalHeaderLabels(["Timestamp", "Type ID"])
        
        for i in range(n):
            try:
                cur_time = datetime.strptime(
                    self.data_view[i]["Timestamp"],
                    '%Y-%m-%d  %H:%M:%S.%f')
            except Exception as e:
                cur_time = datetime.strptime(
                    self.data_view[i]["Timestamp"], '%Y-%m-%d  %H:%M:%S')
            self.min_time = min(self.min_time, cur_time)
            self.max_time = max(self.max_time, cur_time)
            
            # Set cell values
            timestamp_item = QTableWidgetItem(str(self.data_view[i]["Timestamp"]))
            timestamp_item.setFlags(timestamp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.grid.setItem(i, 0, timestamp_item)
            
            typeid_item = QTableWidgetItem(str(self.data_view[i]["TypeID"]))
            typeid_item.setFlags(typeid_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.grid.setItem(i, 1, typeid_item)


def main():
    app = QApplication(sys.argv)
    window = WindowClass()
    sys.exit(app.exec())


main()
