#  _______________________________________
# | Program : LHL an Amateur Radio Log    |
# | Author : Ac1ne                        |
# |_______________________________________|
#

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMessageBox, QWidgetAction, QStyledItemDelegate, QStyle, QMenu, QFileDialog
from PyQt5.QtCore import Qt, QTimer, QTime, QDate, QRegExp, QFile, QTextStream, QEvent, QDateTime
from PyQt5.QtGui import QFont, QRegExpValidator, QGuiApplication, QIntValidator, QCursor, QBrush, QColor, QPainter
import datetime
import json
import os
import calendar
from datetime import timezone

### DPI setup for monitor resolution 
QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

### Line Number Format
class IntegerDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        regex = QRegExp(r'\d{1,4}(\.\d{0,2})?')
        validator = QRegExpValidator(regex)
        editor.setValidator(validator)
        return editor
        
### Time Format

class TimeDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setInputMask("00:00")
        return editor

    def setModelData(self, editor, model, index):
        text = editor.text()
        valid = False

        if ':' in text:
            try:
                h, m = map(int, text.split(":"))
                if 0 <= h <= 23 and 0 <= m <= 59:
                    valid = True
            except ValueError:
                pass
       
        if valid:
            formatted = f"{h:02d}:{m:02d}"
            model.setData(index, formatted, Qt.EditRole)
        else:
            QMessageBox.warning(editor, "Invalid Time", "Time is out of range. Please enter a valid time (00:00 to 23:59).")
            model.setData(index, text, Qt.EditRole)

### Date Format 

class DateDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setInputMask("0000-00-00")
        return editor

    def setModelData(self, editor, model, index):
        text = editor.text()
        valid = False

        if '-' in text:
            try:
                y, mo, d = map(int, text.split("-"))
                if 1 <= mo <= 12:
                    max_day = calendar.monthrange(y, mo)[1]
                    if 1 <= d <= max_day:
                        valid = True
            except ValueError:
                pass

        if valid:
            formatted = f"{y:04d}-{mo:02d}-{d:02d}"
            model.setData(index, formatted, Qt.EditRole)
        else:
            QMessageBox.warning(editor, "Invalid Date", "Date is out of range. Please enter a valid date (YYYY-MM-DD).")
            model.setData(index, text, Qt.EditRole)

 ### Date Format       
class DateTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        self_date = QDate.fromString(self.text(), "yyyy-MM-dd")
        other_date = QDate.fromString(other.text(), "yyyy-MM-dd")
        return self_date < other_date

### Letter With Numbers and Symbols 
class AlphanumericDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setMaxLength(9)
        editor.textChanged.connect(self.onTextChanged)  
        return editor
        
### Sets Letters to upper case view only
    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        value = (value or "").upper() 
        editor.setText(value)   
 
    def onTextChanged(self, text):        
        editor = self.sender()
        if editor:
            editor.setText(text.upper())
            
### Numbers with Decimals Symbol Only
class NumericWithDecimalDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        regex = QRegExp(r'[0-9]+(\.[0-9]{0,9})?')
        validator = QRegExpValidator(regex)
        editor.setValidator(validator)
        editor.setMaxLength(9)
        return editor

### Numberts with a Specific Symbol (-,+) Only
class NumericWithSymbolsDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        regex = QRegExp(r'[+-]?\d{0,3}')
        validator = QRegExpValidator(regex)
        editor.setValidator(validator)
        editor.setMaxLength(4)
        return editor

### Sorting of Table Items to ensure Numeric Sort by Value
class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)
        self.numeric_value = self.parse_value(text) 

    def parse_value(self, text):
        try:
            return float(text)
        except ValueError:
            return 0  

    def setData(self, role, value):
        if role == Qt.DisplayRole:
            if isinstance(value, (int, float)):                
                if self.column() == 6:
                    display_text = f"{value:.3f}" 
                elif self.column() in [7, 8]:
                    display_text = f"{int(value)}"  
                elif self.column() == 9:
                    display_text = f"{value:.2f}" if '.' in str(value) else f"{int(value)}"  
                else:
                    display_text = str(value)
                super().setData(role, display_text)
            else:
                super().setData(role, value)
        else:
            super().setData(role, value)

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):           
            if self.numeric_value is not None and other.numeric_value is not None:
                return self.numeric_value < other.numeric_value           
            elif self.numeric_value is None and other.numeric_value is not None:
                return False
            elif self.numeric_value is not None and other.numeric_value is None:
                return True
            return super().__lt__(other)
        return super().__lt__(other)
  
### Dropdown Menus in table editor
class DropdownDelegate(QStyledItemDelegate):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        editor.currentIndexChanged.connect(lambda: self.commitData.emit(editor))
        editor.installEventFilter(self)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        if isinstance(editor, QComboBox):
            idx = editor.findText(value)
            if idx >= 0:
                editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentText(), Qt.EditRole)

    def eventFilter(self, editor, event):
        if isinstance(editor, QComboBox):
            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                    self.commitData.emit(editor)
                    self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)
                    return True 
        return super().eventFilter(editor, event)

### Table Items Format and Sorting   
class TimeTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        return QTime.fromString(self.text(), "HH:mm") < QTime.fromString(other.text(), "HH:mm")

class DateTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        return QDate.fromString(self.text(), "yyyy-MM-dd") < QDate.fromString(other.text(), "yyyy-MM-dd")

class CallTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        return self.text() < other.text()

class ModeTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        return self.text() < other.text()

class BandTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        return self.text() < other.text()
    
class BandTableWidgetItem(QTableWidgetItem):
    BAND_ORDER = {
        "160m": 1,
        "80m": 2,
        "60m": 3,
        "40m": 4,
        "30m": 5,
        "20m": 6,
        "17m": 7,
        "15m": 8,
        "12m": 9,
        "10m": 10,
        "6m": 11,
        "2m": 12,
        "70cm": 14,

    }
    def __lt__(self, other):
        if isinstance(other, BandTableWidgetItem):
            return self.BAND_ORDER[self.text()] < self.BAND_ORDER[other.text()]
        return super().__lt__(other)

### Delegation for Deleting a Row
class HighlightAndDeleteDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            table = index.model().parent()
            table.selectRow(index.row())            
            parent_widget = table.parent()
            if parent_widget.edit_mode:
                parent_widget.show_context_menu(index.row())
        return False    

## Blocks table focus
class NoFocusDelegate(QStyledItemDelegate):
    """Custom delegate to prevent selection and focus in QTableWidget."""
    def paint(self, painter, option, index):
        if option.state & QStyle.State_Selected:
            option.state ^= QStyle.State_Selected
        super().paint(painter, option, index)
 
class BlankTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUI()

### Colors and Borders
    def initUI(self):
        self.setStyleSheet("""
            QTableWidget { 
                border: 2px solid black; 
                background-color: #d3d3d3; 
            }
            QHeaderView::section { 
                background-color: #808080; 
                color: black; 
            }
            QTableView::item {
                border-bottom: 1px solid #808080; /* Horizontal grid lines */
            }         
            QHeaderView:vertical {
                border: none; /* Hide vertical grid lines */
            }
            QTableWidget::item:selected { 
                background-color: #a9a9a9; 
                color: black;
            }           
        """)
    
    
### Table Behavoir
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(True)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setSelectionBehavior(QTableWidget.SelectItems)
        self.setFocusPolicy(Qt.StrongFocus)
        self.verticalScrollBar().setEnabled(True)  
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  
        self.setShowGrid(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)


### Data Format and Behavoir
    def addItemCentered(self, row, col, item):
        try:
            value = float(item)
        except ValueError:
            value = 0  
        if col == 6:  # Freq
            formatted_value = f"{value:.3f}"  
            table_item = NumericTableWidgetItem(formatted_value)
        elif col in [7, 8]: # RX,Tx
            formatted_value = f"{int(value)}"  
            table_item = NumericTableWidgetItem(formatted_value)
        elif col == 9:  # PWR
            formatted_value = f"{value:.2f}" if '.' in str(item) else f"{int(value)}"
            table_item = NumericTableWidgetItem(formatted_value)
        elif col == 5:  # Band
            table_item = BandTableWidgetItem(item)
        else:
            table_item = QTableWidgetItem(item)

        table_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, col, table_item)

### Columns and Rows
    def setColumnWidths(self, widths):
        for col, width in widths.items():
            self.setColumnWidth(col, width)

    def setHeaderAndRowHeight(self, header_height, row_height):
        self.horizontalHeader().setFixedHeight(header_height)
        self.verticalHeader().setDefaultSectionSize(row_height)
        
        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Tab:
                current_index = self.currentIndex()
                column_count = self.columnCount()

                if current_index.column() == column_count - 1:
                    next_row = current_index.row() + 1
                    if next_row < self.rowCount():
                        self.setCurrentCell(next_row, 0)
                else:
                    super().keyPressEvent(event)
            else:
                super().keyPressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
                    
### File related flags
        self.edit_mode = False         
        self.file_created = False
        self.file_loaded = False
        self.time_update_paused = False
        self.original_cell_value = None
        
### Main window properties        
        self.setWindowTitle(" LHL ")
        self.setGeometry(50, 50, 800, 500)  
        self.setFixedSize(800, 450)  
        self.setStyleSheet("background-color: #a9a9a9;")  
        
### Menubar Background        
        menubar = self.menuBar()
        menubar.setStyleSheet("background-color: #808080; border-bottom: 1px solid black;")  

### File menu

### Menu           
        file_menu = menubar.addMenu('File')
        
### New
        new_action = QAction('New', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.reset_form)  
        file_menu.addAction(new_action)       
        
### Load
        load_action = QAction('Load', self)
        load_action.setShortcut('Ctrl+L')
        load_action.triggered.connect(self.load_file)  
        file_menu.addAction(load_action)
        
### Edit
        edit_action = QAction('Edit', self)
        edit_action.setShortcut('Ctrl+E')
        edit_action.triggered.connect(self.toggle_edit_mode)
        file_menu.addAction(edit_action)
        
### Export
        export_action = QAction('Export', self)
        export_action.setShortcut('Ctrl+X')
        export_action.triggered.connect(self.export_adi)  
        file_menu.addAction(export_action)
        
### Exit
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

### Gui Objects (Lables, Input Fields, Tables, and Buttons
        
### Call Sign       
        self.label_mycall = QLabel("My Call:", self)
        self.label_mycall.setGeometry(10, 30, 60, 25)                   

        self.mycall = QLineEdit(self)
        self.mycall.setGeometry(65, 30, 75, 25) 
        self.mycall.setStyleSheet("background-color: #d3d3d3;")
        self.mycall.setMaxLength(7)  
        self.mycall.setAlignment(Qt.AlignCenter)  
        self.mycall.setFont(QFont("Arial", 10))
        self.mycall.setPlaceholderText("Call Sign")
        self.mycall.textChanged.connect(self.uppercase_text_mycall)
        
### Grid Square          
        self.label_grid = QLabel("Grid Square: ", self)
        self.label_grid.setGeometry(150, 30, 75, 25) 
        
        self.grid = QLineEdit(self)
        self.grid.setGeometry(230, 30, 60, 25)
        self.grid.setStyleSheet("background-color: #d3d3d3;")
        self.grid.setMaxLength(7) 
        self.grid.setAlignment(Qt.AlignCenter)  
        self.grid.setFont(QFont("Arial", 10))
        self.grid.setPlaceholderText("Grid")
        self.grid.textChanged.connect(self.uppercase_text_grid)

### Create       
        self.create_button = QPushButton("Create", self)
        self.create_button.setGeometry(300, 30, 75, 25) 
        self.create_button.setStyleSheet("background-color: #d3d3d3;")
        self.create_button.clicked.connect(self.create_file)
        
### Table
        self.log = BlankTableWidget(self)
        self.log.setGeometry(10, 70, 780, 285)  
        self.log.setColumnCount(11)
        self.log.setHorizontalHeaderLabels(["#", "Time", "Date", "Call", "Mode", "Band", "Freq", "Tx", "Rx", "Pwr", "QSO"])               
        self.log.setColumnWidths({
            0: 50,  
            1: 50,   
            2: 100,  
            3: 75,  
            4: 75,  
            5: 75,   
            6: 75,   
            7: 65,  
            8: 65,  
            9: 65,  
            10: 65,  
        })
        
        self.log.horizontalHeader().sectionClicked.connect(self.enable_sorting_on_user_click)
        self.log.setSortingEnabled(True)
        self.log.cellClicked.connect(self.on_cell_clicked)
        self.log.currentCellChanged.connect(self.on_cell_edit_start_from_navigation)
        self.log.itemChanged.connect(self.on_cell_edit_end)
        self.log.setItemDelegateForColumn(0, HighlightAndDeleteDelegate(self.log))      
        self.log.setSortingEnabled(True) 

### Local Time
        self.label_local_time = QLabel("Local Time:",self)
        self.label_local_time.setGeometry(585,433,75,15)
        
        self.label_local_time_date = QLabel(self)
        self.label_local_time_date.setGeometry(655, 434, 130, 15)  
        self.label_local_time_date.setFont(QFont("Arial", 10))
        self.label_local_time_date.setStyleSheet("background-color: #a9a9a9;")
        self.label_local_time_date.setAlignment(Qt.AlignCenter)        
        self.timer_local_time_date = QTimer(self)
        self.timer_local_time_date.timeout.connect(self.update_local_time_date)
        self.timer_local_time_date.start(1000)        
        self.update_local_time_date()
        
### Time  
        self.label_time = QLabel("Time UTC", self)
        self.label_time.setGeometry(35, 366, 60, 25)

        self.time = QLineEdit(self)
        self.time.setGeometry(105, 365, 80, 25)  
        self.time.setStyleSheet("background-color: #d3d3d3;")
        self.time.setAlignment(Qt.AlignCenter) 
        self.time.setFont(QFont("Arial", 10))
        self.time.setPlaceholderText("HH:MM")
        self.time.setInputMask("00:00")        
        self.time.editingFinished.connect(self.format_time_field)             
        self.timer_time = QTimer(self)
        self.timer_time.timeout.connect(self.update_time)
        self.timer_time.start(1000)  
        self.update_time()        
        self.time_update_paused = False       
        self.time.installEventFilter(self)

        
### Date        
        self.label_date = QLabel("Date UTC", self)
        self.label_date.setGeometry(35, 400, 60, 25)  

        self.date = QLineEdit(self)
        self.date.setGeometry(105, 400, 80, 25) 
        self.date.setStyleSheet("background-color: #d3d3d3;")
        self.date.setAlignment(Qt.AlignCenter)  
        self.date.setFont(QFont("Arial", 10))
        self.date.setPlaceholderText("yyyy-MM-dd")
        self.date.setInputMask("0000-00-00")        
        self.date.editingFinished.connect(self.format_date_field)        
        self.timer_date = QTimer(self)
        self.timer_date.timeout.connect(self.update_date)
        self.timer_date.start(300000)        
        self.update_date()
        
### Timer for updating the time
        self.timer_time = QTimer(self)
        self.timer_time.timeout.connect(self.update_time)
        self.timer_time.start(1000)
        self.update_time()
        
### Call 
        self.label_call = QLabel("Call:", self)
        self.label_call.setGeometry(207, 365, 60, 25)  

        self.call = QLineEdit(self)
        self.call.setGeometry(243, 365, 85, 25)  
        self.call.setStyleSheet("background-color: #d3d3d3;")
        self.call.setAlignment(Qt.AlignCenter)  
        self.call.setFont(QFont("Arial", 10))
        self.call.setPlaceholderText("Call Sign")
        self.call.setMaxLength(7)  
        self.call.textChanged.connect(self.uppercase_text_call)
        
### Mode
        self.label_mode = QLabel("Mode:", self)
        self.label_mode.setGeometry(199, 400, 60, 25) 

        self.mode = QComboBox(self)
        self.mode.setGeometry(243, 400, 85, 25) 
        self.mode.setStyleSheet("background-color: #d3d3d3;")
        self.mode.addItems(["SSB", "CW", "AM", "FM", "FT-8","WSPR"])
    
### Band
        self.label_band = QLabel("Band:", self)
        self.label_band.setGeometry(340, 365, 60, 25) 
        
        self.band = QComboBox(self)
        self.band.setGeometry(379, 365, 70, 25)  
        self.band.setStyleSheet("background-color: #d3d3d3;")
        self.band.addItems(["160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "10m", "12m", "6m", "2m", "70cm"]) 
        
### Freq       
        self.label_Freq = QLabel("Freq:", self)
        self.label_Freq.setGeometry(340, 400, 60, 25)

        self.freq = QLineEdit(self)
        self.freq.setGeometry(379, 400, 70, 25) 
        self.freq.setStyleSheet("background-color: #d3d3d3;")
        self.freq.setAlignment(Qt.AlignCenter)  
        self.freq.setFont(QFont("Arial", 10))
        self.freq.setPlaceholderText("Freq")
        self.freq.setValidator(QRegExpValidator(QRegExp("^\\d{0,6}(\\.\\d{0,6})?$"), self))        

### TX
        self.label_tx = QLabel("Tx:", self)
        self.label_tx.setGeometry(465, 365, 60, 25)

        self.tx = QLineEdit(self)
        self.tx.setGeometry(495, 365, 60, 25)  
        self.tx.setStyleSheet("background-color: #d3d3d3;")
        self.tx.setAlignment(Qt.AlignCenter) 
        self.tx.setFont(QFont("Arial", 10))
        self.tx.setPlaceholderText("Tx")
        self.tx.setValidator(QRegExpValidator(QRegExp("[+-]?\\d{0,3}"), self))
        
### RX
        self.label_rx = QLabel("Rx:", self)
        self.label_rx.setGeometry(465, 400, 60, 25)  

        self.rx = QLineEdit(self)
        self.rx.setGeometry(495, 400, 60, 25)  
        self.rx.setStyleSheet("background-color: #d3d3d3;")
        self.rx.setAlignment(Qt.AlignCenter)  
        self.rx.setFont(QFont("Arial", 10))
        self.rx.setPlaceholderText("Rx")
        self.rx.setValidator(QRegExpValidator(QRegExp("[+-]?\\d{0,3}"), self))
        
### PWR
        self.label_pwr = QLabel("Pwr:", self)
        self.label_pwr.setGeometry(562, 365, 60, 25)  

        self.pwr = QLineEdit(self)
        self.pwr.setGeometry(600, 365, 70, 25)  
        self.pwr.setStyleSheet("background-color: #d3d3d3;")
        self.pwr.setAlignment(Qt.AlignCenter)  
        self.pwr.setFont(QFont("Arial", 10))
        self.pwr.setPlaceholderText("Watts")
        self.pwr.setValidator(QRegExpValidator(QRegExp("^\\d{0,4}(\\.\\d{0,3})?$"), self))
        
### QSO
        self.label_qso = QLabel("QSO:", self)
        self.label_qso.setGeometry(562, 400, 60, 25) 

        self.qso = QComboBox(self)
        self.qso.setGeometry(600, 400, 70, 25) 
        self.qso.setStyleSheet("background-color: #d3d3d3;")
        self.qso.addItems(["Sent", "Rcvd"])
        self.qso.currentTextChanged.connect(self.uppercase_text_qso)
        
### Update Button      
        self.update_button = QPushButton("Update", self)
        self.update_button.setGeometry(685, 365, 75, 25)  
        self.update_button.setStyleSheet("background-color: #d3d3d3;")
        self.update_button.clicked.connect(self.update_data)
        
### Clear Data Button      
        self.clear_data_button = QPushButton("Clear", self)
        self.clear_data_button.setGeometry(685, 400, 75, 25)  
        self.clear_data_button.setStyleSheet("background-color: #d3d3d3;")
        self.clear_data_button.clicked.connect(self.clear_data)
        
       
### Search
        self.search = QLineEdit(self)
        self.search.setGeometry(470, 30, 100, 25) 
        self.search.setStyleSheet("background-color: #d3d3d3;")
        self.search.setAlignment(Qt.AlignCenter)
        self.search.setFont(QFont("Arial", 10))
        self.search.setPlaceholderText("Search")
        self.search.textChanged.connect(self.uppercase_text_search)

### Button Search
        self.search_button = QPushButton("Search", self)
        self.search_button.setGeometry(580, 30, 100, 25)  
        self.search_button.setStyleSheet("background-color: #d3d3d3;")
        self.search_button.clicked.connect(self.search_log)

### Button Clear Search
        self.clear_search_button = QPushButton("Clear Search", self)
        self.clear_search_button.setGeometry(690, 30, 100, 25)  
        self.clear_search_button.setStyleSheet("background-color: #d3d3d3;")
        self.clear_search_button.clicked.connect(self.clear_search)
       
### Done_Edit   
        self.done_button = QPushButton('Done', self)
        self.done_button.setGeometry(390, 400, 75, 25)
        self.done_button.setStyleSheet("background-color: #d3d3d3;")
        self.done_button.setVisible(False) 
        self.done_button.clicked.connect(self.save_edits)
        
### Cancel_Edit        
        self.cancel_edit_button = QPushButton('Cancel', self)
        self.cancel_edit_button.setGeometry(310, 400, 75, 25)
        self.cancel_edit_button.setStyleSheet("background-color: #d3d3d3;")
        self.cancel_edit_button.setVisible(False) 
        self.cancel_edit_button.clicked.connect(self.cancel_edit_mode)
        
### Add_Row
        self.add_button = QPushButton("Add Row", self)
        self.add_button.setGeometry(35, 366, 75, 25)
        self.add_button.setStyleSheet("background-color: #d3d3d3;")
        self.add_button.setVisible(False)
        self.add_button.clicked.connect(self.add_row)    
    
### Initialize row count for table
        self.row_count = 0
        
## Key Press Events       
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if isinstance(self.focusWidget(), QPushButton):
                self.focusWidget().click()
            elif self.edit_mode and self.log.hasFocus():
                current_item = self.log.currentItem()
                if current_item:
                    self.log.editItem(current_item)
        else:
            super().keyPressEvent(event)
            
    def eventFilter(self, obj, event):
        if obj == self.time and event.type() == event.KeyPress:
            if event.key() != Qt.Key_Tab:
                self.time_update_paused = True
        return super().eventFilter(obj, event)
            
### Upper Case Letters    
    def uppercase_text_mycall(self, text):
        self.mycall.setText(text.upper())

    def uppercase_text_grid(self, text):
        self.grid.setText(text.upper())

    def uppercase_text_call(self, text):
        self.call.setText(text.upper())

    def uppercase_text_qso(self, text):
        self.qso.setCurrentText(text.capitalize())
        
    def uppercase_text_search(self, text):
        self.search.setText(text.upper())
        
### Local Time and Date        
    def update_local_time_date(self):        
        now_local = datetime.datetime.now()
        local_time_date = now_local.strftime("%Y-%m-%d   %H:%M:%S")        
        self.label_local_time_date.setText(local_time_date)    
    
    def eventFilter(self, obj, event):
        if obj == self.time and event.type() == event.KeyPress:
            if event.key() != Qt.Key_Tab:
                self.time_update_paused = True
        return super().eventFilter(obj, event)
 
### Time Format
    def format_time_field(self):
        text = self.time.text().strip()
        if ":" in text:
            parts = text.split(":")
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                h, m = map(int, parts)
                if 0 <= h <= 23 and 0 <= m <= 59:
                    self.time.setText(f"{h:02d}:{m:02d}")
                else:
                    QMessageBox.warning(self, "Invalid Time", "Time is out of range. Please enter a valid time (00:00 to 23:59).")
            else:
                QMessageBox.warning(self, "Invalid Time", "Time format is incorrect. Please use HH:MM.")

### Date Format
    def format_date_field(self):
        text = self.date.text().strip()
        if "-" in text:
            parts = text.split("-")
            if len(parts) == 3 and all(part.isdigit() for part in parts):
                y, mo, d = map(int, parts)
                if 1 <= mo <= 12:
                    max_day = calendar.monthrange(y, mo)[1]
                    if 1 <= d <= max_day:
                        self.date.setText(f"{y:04d}-{mo:02d}-{d:02d}")
                    else:
                        QMessageBox.warning(self, "Invalid Date", "Day is out of range for the given month and year.")
                else:
                    QMessageBox.warning(self, "Invalid Date", "Month is out of range. Please enter a valid date (YYYY-MM-DD).")
            else:
                QMessageBox.warning(self, "Invalid Date", "Date format is incorrect. Please use YYYY-MM-DD.")

### Time Updates
    def update_time(self):
        if not self.time_update_paused:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            current_time = now_utc.strftime("%H:%M")
            previous_time = self.time.text()
            self.time.setText(current_time)
            if previous_time == "23:59" and current_time == "00:00":
                self.update_date()
### Date Updates
    def update_date(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        current_date = now_utc.strftime("%Y-%m-%d")
        self.date.setText(current_date)
    
### Window Title 
    def update_window_title(self):
        if self.file_name:
            self.setWindowTitle(f"LHL : {self.file_name}")
                   
### Delete Row
    def on_cell_clicked(self, row, column):
        if column == 0 and self.edit_mode:
            self.log.selectRow(row)
            self.show_context_menu(row)

    def show_context_menu(self, row):
        menu = QMenu(self)
        delete_action = QAction("Delete Row", self)
        delete_action.triggered.connect(lambda: self.show_delete_confirmation_dialog(row))  
        menu.addAction(delete_action)
        menu.exec_(QCursor.pos())

    def show_delete_confirmation_dialog(self, row):  
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Delete Current Row")
        msg_box.setText("Are you sure?")
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = msg_box.exec_()

        if result == QMessageBox.Yes:
            self.delete_row(row)

    def delete_row(self, row):
        self.log.removeRow(row)

### Table Sorting       
    def enable_sorting_on_user_click(self, index):
        self.log.setSortingEnabled(True)
 
    def on_cell_edit_start_from_navigation(self, current_row, current_column, previous_row, previous_column):
        item = self.log.item(current_row, current_column)
        if item:
            self.original_cell_value = item.text()
            self.log.setSortingEnabled(False)
            
            if current_column in [6, 7, 8, 9]:  # Freq, Tx, Rx, Pwr
                item.setTextAlignment(Qt.AlignCenter)
                
    def on_cell_edit_end(self, item):
        if not self.edit_mode or item is None:
            return

        original_value = item.data(Qt.UserRole)
        if original_value is not None and item.text() != original_value:
            item.setForeground(QBrush(QColor("blue")))
        else:
            item.setForeground(QBrush(QColor("black")))
            
                
## Create New Form
    def on_new_triggered(self):
        if self.edit_mode:
            QMessageBox.warning(self, "Warning", "You must exit edit mode to perform this action.")    
        else:
            self.reset_form()  
  
### Create .json
    def create_file(self):
        if self.mycall.text().strip() == '' or self.grid.text().strip() == '':
            QMessageBox.warning(self, "Warning", "Please fill in MyCall and Grid fields.")
            return
 
        file_dialog = QFileDialog(self)
        file_dialog.setDefaultSuffix('json') 
        file_dialog.setFileMode(QFileDialog.AnyFile)
        file_dialog.setNameFilter("JSON files (*.json)")
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)    

        if file_dialog.exec_() == QFileDialog.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            if not file_path.lower().endswith('.json'): 
                file_path += '.json'        
            self.file_name = file_path
            with open(self.file_name, 'w') as file:
                file.write(json.dumps({"mycall": self.mycall.text(), "grid": self.grid.text(), "log": []})) 
    
            self.file_created = True
            self.create_button.setVisible(False)
            self.mycall.setReadOnly(True)
            self.grid.setReadOnly(True)
        else:
            self.reset_form()
 
### Updating Data
    def update_data(self):
        self.clear_search()    
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        current_time = now_utc.strftime("%H:%M")
        current_date = now_utc.strftime("%Y-%m-%d")
        
### Reterives Data        
        time_text = self.time.text()
        date_text = self.date.text()
        mycall_text = self.mycall.text()
        grid_text = self.grid.text()
        call_text = self.call.text()
        mode_text = self.mode.currentText()
        band_text = self.band.currentText()
        freq_text = self.freq.text()
        tx_text = self.tx.text()
        rx_text = self.rx.text()
        pwr_text = self.pwr.text()
        qso_text = self.qso.currentText()
        
### Check if fields are empty and set to 0
        if not freq_text:
            freq_text = 0
        if not tx_text:
            tx_text = 0
        if not rx_text:
            rx_text = 0
        if not pwr_text:
            pwr_text = 0
    
### Disables Sorting 
        self.log.setSortingEnabled(False)
        self.time.setFocus()
        
### Checks File was Created    
        if not hasattr(self, 'file_name'):
            QMessageBox.warning(self, "File Not Created", "Please create a file first using the 'Create' button.")
            return
        
### Load Existing Data
        with open(self.file_name, 'r') as file:
            data = json.load(file)           
            self.log.setSortingEnabled(False)

### Append New Log Entry
        data['log'].append({
            'time': time_text,
            'date': date_text,
            'call': call_text,
            'mode': mode_text,
            'band': band_text,
            'freq': freq_text,
            'tx': tx_text,
            'rx': rx_text,
            'pwr': pwr_text,
            'qso': qso_text
        })

### Write Update to File
        with open(self.file_name, 'w') as file:
            json.dump(data, file, indent=4)

### Insert New Table Row
        self.log.insertRow(0)
        self.log.addItemCentered(0, 0, f"{len(data['log']):04d}")  
        self.log.addItemCentered(0, 1, time_text)
        self.log.addItemCentered(0, 2, date_text)
        self.log.addItemCentered(0, 3, call_text)
        self.log.addItemCentered(0, 4, mode_text)
        self.log.addItemCentered(0, 5, band_text)
        self.log.addItemCentered(0, 6, str(freq_text))
        self.log.addItemCentered(0, 7, str(tx_text))
        self.log.addItemCentered(0, 8, str(rx_text))
        self.log.addItemCentered(0, 9, str(pwr_text))
        self.log.addItemCentered(0, 10, qso_text)
        self.log.setRowHeight(0, 20)

### Clear Call, Tx, Rx Lines Enable Sorting
        self.call.clear()       
        self.tx.clear()
        self.rx.clear()
        self.log.sortItems(0, Qt.DescendingOrder)
        self.log.setSortingEnabled(True)
        self.time.setFocus()
        self.time.setText(current_time)
        self.date.setText(current_date)
        
        self.time_update_paused = False
        self.update_time()
      
        
        self.log.setSortingEnabled(True)
        
    def clear_data(self):
        self.call.clear()
        self.freq.clear()
        self.tx.clear()
        self.rx.clear()
        self.pwr.clear()
        self.mode.setCurrentText("SSB")
        self.band.setCurrentText("160m")
        self.qso.setCurrentText("Sent")        
 
    def enable_sorting_on_user_click(self, index):
        self.log.setSortingEnabled(True)        
        self.update_time()
        self.update_date()
        self.time_update_paused = False
        self.update_time()       
       
### Loading File Existing File

    def load_file(self):
        if self.edit_mode:
            self.show_edit_mode_warning()
            return
            
### Open File Dialog Default .json
        file_dialog = QFileDialog(self)
        file_dialog.setDefaultSuffix('json')  
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("JSON files (*.json)")        
   
        if file_dialog.exec_() == QFileDialog.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            self.file_name = file_path
            self.log.setSortingEnabled(False) 
            self.log.setRowCount(0)

            with open(self.file_name, 'r') as file:
                data = json.load(file)
                mycall = data.get('mycall', '')
                grid = data.get('grid', '')
                log_entries = data.get('log', [])
                self.mycall.setText(mycall)
                self.grid.setText(grid)

### Populate Table Reversed Order
                for i, entry in enumerate(reversed(log_entries)):            
                    row_position = self.log.rowCount()
                    self.log.insertRow(row_position)
                    self.log.addItemCentered(row_position, 0, f"{len(log_entries) - i:04d}")
                    self.log.addItemCentered(row_position, 1, entry['time'])
                    self.log.addItemCentered(row_position, 2, entry['date'])
                    self.log.addItemCentered(row_position, 3, entry['call'])
                    self.log.addItemCentered(row_position, 4, entry['mode'])
                    self.log.addItemCentered(row_position, 5, entry['band'])
                    self.log.addItemCentered(row_position, 6, entry['freq'])
                    self.log.addItemCentered(row_position, 7, entry['tx'])
                    self.log.addItemCentered(row_position, 8, entry['rx'])
                    self.log.addItemCentered(row_position, 9, entry['pwr'])
                    self.log.addItemCentered(row_position, 10, entry['qso'])
                    self.log.setRowHeight(row_position, 20)
                                            
### Visibility Create Button
            self.file_loaded = True
            self.create_button.setVisible(False)

### Disable Editing and Enable Sorting
            self.mycall.setReadOnly(True)
            self.grid.setReadOnly(True)
            self.log.sortItems(0, Qt.DescendingOrder)
            self.log.setSortingEnabled(True)  
            self.time.setFocus()

### Reset Form if Canceled    
        else:
            if not self.file_loaded:
                self.reset_form()

## Reset form to initial state
    def reset_form(self):
        if self.edit_mode:
            self.show_edit_mode_warning()
            return
        
        self.mycall.clear()
        self.grid.clear()
        self.call.clear()
        self.freq.clear()
        self.tx.clear()
        self.rx.clear()
        self.pwr.clear()
        self.qso.setCurrentIndex(0)
        self.log.setRowCount(0)
        self.mycall.setReadOnly(False)
        self.grid.setReadOnly(False)
        self.create_button.setVisible(True)
        
        if hasattr(self, 'file_name'):
            delattr(self, 'file_name')
        
        self.file_created = False
        self.file_loaded = False
        self.mycall.setFocus()
        
## Search Function      
    def search_log(self):
        search_term = self.search.text().strip().lower()
        if not search_term:
            QMessageBox.warning(self, "Input Error", "Please enter a search term.")
            return                
        matches = []
        for row in range(self.log.rowCount()):       
            row_data = [
                self.log.item(row, col).text().lower() if self.log.item(row, col) else ""
                for col in range(self.log.columnCount())
            ]
            
### Check for Search Term
            if any(search_term in cell for cell in row_data):
                matches.append(row)
    
### Hide Rows That Don't Match
        if matches:
            for row in range(self.log.rowCount()):
                self.log.setRowHidden(row, row not in matches)
        else:
            QMessageBox.information(self, "No Matches", f"No matches found for '{search_term}'.")
            
### Clearing Search
    def clear_search(self):
        self.search.clear()
        for row in range(self.log.rowCount()):
            self.log.setRowHidden(row, False)
 
### Add Row in Edit
    def add_row(self):
        self.log.setSortingEnabled(False)
        row_position = 0
        self.log.insertRow(row_position)
        item = QTableWidgetItem("")
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(QBrush(QColor("blue")))
        self.log.setItem(row_position, 0, item)

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        placeholders = [
            now_utc.strftime("%H:%M"), 
            now_utc.strftime("%Y-%m-%d"), 
            "CALL", "SSB", "20m", "14.000", "59", "59", "100", "Sent"
        ]
        for col, value in enumerate(placeholders, start=1):
            placeholder_item = QTableWidgetItem(value)
            placeholder_item.setTextAlignment(Qt.AlignCenter)
            placeholder_item.setForeground(QBrush(QColor("blue"))) 
            self.log.setItem(row_position, col, placeholder_item)
            
## Editing             
    def toggle_edit_mode(self):
        if not self.file_loaded and not self.file_created:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("No file loaded. Load a file first.")
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setStandardButtons(QMessageBox.Ok)

            def close_message_box():
                self.edit_mode = False                
                self.done_button.setVisible(False)
                self.add_button.setVisible(False)
                self.cancel_edit_button.setVisible(False)
                self.log.setEditTriggers(QTableWidget.NoEditTriggers)
                self.mycall.setReadOnly(True)
                self.grid.setReadOnly(True)

            msg_box.finished.connect(close_message_box)
            msg_box.exec_()
        else:
            self.edit_mode = not self.edit_mode
            self.done_button.setVisible(self.edit_mode)
            self.cancel_edit_button.setVisible(self.edit_mode)
            self.add_button.setVisible(self.edit_mode)
            self.log.setEditTriggers(QTableWidget.DoubleClicked if self.edit_mode else QTableWidget.NoEditTriggers)
            self.mycall.setReadOnly(not self.edit_mode)
            self.grid.setReadOnly(not self.edit_mode)
            self.label_time.setVisible(not self.edit_mode)

            self.time.setVisible(not self.edit_mode)
            self.label_time.setVisible(not self.edit_mode)
            self.date.setVisible(not self.edit_mode)
            self.label_date.setVisible(not self.edit_mode)
            self.call.setVisible(not self.edit_mode)
            self.label_call.setVisible(not self.edit_mode)
            self.mode.setVisible(not self.edit_mode)
            self.label_mode.setVisible(not self.edit_mode)
            self.band.setVisible(not self.edit_mode)
            self.label_band.setVisible(not self.edit_mode)
            self.freq.setVisible(not self.edit_mode)
            self.label_Freq.setVisible(not self.edit_mode)
            self.tx.setVisible(not self.edit_mode)
            self.label_tx.setVisible(not self.edit_mode)
            self.rx.setVisible(not self.edit_mode)
            self.label_rx.setVisible(not self.edit_mode)
            self.pwr.setVisible(not self.edit_mode)
            self.label_pwr.setVisible(not self.edit_mode)
            self.qso.setVisible(not self.edit_mode)
            self.label_qso.setVisible(not self.edit_mode)
            self.update_button.setVisible(not self.edit_mode)
            self.clear_data_button.setVisible(not self.edit_mode)
            

            if self.edit_mode:
                self.log.setItemDelegateForColumn(0, HighlightAndDeleteDelegate(self.log))
                self.log.setItemDelegateForColumn(1, TimeDelegate(self.log))
                self.log.setItemDelegateForColumn(2, DateDelegate(self.log))
                self.log.setItemDelegateForColumn(3, AlphanumericDelegate(self.log))
                self.log.setItemDelegateForColumn(4, DropdownDelegate(["SSB", "CW", "AM", "FM", "FT-8", "WSPR"], self.log))
                self.log.setItemDelegateForColumn(5, DropdownDelegate(["160m", "80m", "40m", "20m", "15m", "10m", "6m", "2m", "70cm"], self.log))
                self.log.setItemDelegateForColumn(6, NumericWithDecimalDelegate(self.log))
                self.log.setItemDelegateForColumn(7, NumericWithSymbolsDelegate(self.log))
                self.log.setItemDelegateForColumn(8, NumericWithSymbolsDelegate(self.log))
                self.log.setItemDelegateForColumn(9, IntegerDelegate(self.log))
                self.log.setItemDelegateForColumn(10, DropdownDelegate(["Sent", "Rcvd"], self.log))

                QMessageBox.information(self, "Edit Mode", "Log Unlocked")
            else:
                self.reload_current_file()       

    def on_cell_edit_end(self, item):
        if not self.edit_mode:
            return
        if item and self.original_cell_value is not None:
            if item.text() != self.original_cell_value:
                item.setForeground(QBrush(QColor("blue")))
            else:
                item.setForeground(QBrush(QColor("black")))
        self.original_cell_value = None
        
### Cancel Edits           
    def cancel_edit_mode(self):
        if not hasattr(self, 'file_name') or not self.file_name:
            return    
        self.reload_current_file()
        self.toggle_edit_mode()        
        QMessageBox.information(self, "Edit Mode", "Changes reverted")

    def reload_current_file(self):
        if hasattr(self, 'file_name') and self.file_name:    
            with open(self.file_name, 'r') as file:
                data = json.load(file)
            self.log.setSortingEnabled(False)
            self.log.setRowCount(0)
            
            for i, entry in enumerate(reversed(data['log'])):            
                row_position = self.log.rowCount()
                self.log.insertRow(row_position)
                self.log.addItemCentered(row_position, 0, f"{len(data['log']) - i:04d}")
                self.log.addItemCentered(row_position, 1, entry['time'])
                self.log.addItemCentered(row_position, 2, entry['date'])
                self.log.addItemCentered(row_position, 3, entry['call'])
                self.log.addItemCentered(row_position, 4, entry['mode'])
                self.log.addItemCentered(row_position, 5, entry['band'])
                self.log.addItemCentered(row_position, 6, entry['freq'])
                self.log.addItemCentered(row_position, 7, entry['tx'])
                self.log.addItemCentered(row_position, 8, entry['rx'])
                self.log.addItemCentered(row_position, 9, entry['pwr'])
                self.log.addItemCentered(row_position, 10, entry['qso'])
                self.log.setRowHeight(row_position, 20)

            self.log.setSortingEnabled(True)
            
    def show_edit_mode_warning(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Warning")
        msg_box.setText("You must exit Edit Mode first.")
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
### Save Edits      
    def save_edits(self):
        if hasattr(self, 'file_name'):
            with open(self.file_name, 'r+') as file:
                data = json.load(file)
                num_rows = self.log.rowCount()
                
                self.log.setSortingEnabled(True)
                self.log.sortItems(0, Qt.AscendingOrder)
                
                for row in range(self.log.rowCount()):
                    for col in range(self.log.columnCount()):
                        item = self.log.item(row, col)
                        if item:
                            item.setForeground(QBrush(QColor("black")))
                rows = []
                for row in range(num_rows):
                    time_item = self.log.item(row, 1)
                    date_item = self.log.item(row, 2)
                    if time_item and date_item:
                        try:
                            row_datetime = datetime.datetime.strptime(
                                f"{date_item.text()} {time_item.text()}", "%Y-%m-%d %H:%M"
                            )
                        except ValueError:
                            row_datetime = datetime.datetime.min
                    else:
                        row_datetime = datetime.datetime.min

                    row_data = [self.log.item(row, col).text() if self.log.item(row, col) else "" for col in range(self.log.columnCount())]
                    rows.append((row_datetime, row_data))
                rows.sort(key=lambda x: x[0])
                self.log.setRowCount(0)
                save_data = []
                for i, (dt, row_data) in enumerate(rows):
                    self.log.insertRow(i)
                    row_id = f"{i+1:04d}"
                    item = QTableWidgetItem(row_id)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.log.setItem(i, 0, item)

                    entry = {}
                    for col, value in enumerate(row_data[1:], start=1):
                        cell_item = QTableWidgetItem(value)
                        cell_item.setTextAlignment(Qt.AlignCenter)
                        self.log.setItem(i, col, cell_item)
                        header = self.log.horizontalHeaderItem(col).text().lower()
                        entry[header] = value
                    entry['#'] = row_id
                    save_data.append(entry)

### Update JSON data
                data['log'] = save_data
                data['mycall'] = self.mycall.text()
                data['grid'] = self.grid.text()
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()

### Reset UI
            self.mycall.setReadOnly(True)
            self.grid.setReadOnly(True)
            self.toggle_edit_mode()
            self.time.setFocus()
            self.log.sortItems(0, Qt.DescendingOrder)

            QMessageBox.information(self, "Edits Saved", "Edits have been saved.")


### Export adi
    
    def export_adi(self):    
        if self.edit_mode:
            self.show_edit_mode_warning()
            return
    
        if not self.file_loaded:  
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("No file loaded. Load a file first.")
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            return    
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save ADIF File", "", "ADIF Files (*.adi);;All Files (*)", options=options)    
        if file_name:
            if not file_name.endswith('.adi'):
                file_name += '.adi'
            last_export_date = QDateTime()

            if os.path.exists(file_name):
                with open(file_name, 'r') as file:
                    lines = file.readlines()
                    for line in lines:
                        if line.startswith("Log exported on:"):
                            last_export_date_str = line[len("Log exported on:"):].strip()
                            last_export_date = QDateTime.fromString(last_export_date_str, 'yyyy-MM-dd HH:mm:ss UTC')
                            break
        
### ADIF Header  
            adi_data = "ADIF Export from LHL Amateur Log 1.0\n"
            adi_data += "Written by Samuel Busenbark\n"
            adi_data += f"Log exported on: {QDateTime.currentDateTimeUtc().toString('yyyy-MM-dd HH:mm:ss')} UTC\n"
            adi_data += "<EOH>\n\n"

### Iterate Log Table
            for row in range(self.log.rowCount()):
                time = self.log.item(row, 1).text() if self.log.item(row, 1) else ""
                date = self.log.item(row, 2).text() if self.log.item(row, 2) else ""
                call = self.log.item(row, 3).text() if self.log.item(row, 3) else ""
                mode = self.log.item(row, 4).text() if self.log.item(row, 4) else ""
                band = self.log.item(row, 5).text() if self.log.item(row, 5) else ""
                freq = self.log.item(row, 6).text() if self.log.item(row, 6) else ""
                tx = self.log.item(row, 7).text() if self.log.item(row, 7) else ""
                rx = self.log.item(row, 8).text() if self.log.item(row, 8) else ""
                pwr = self.log.item(row, 9).text() if self.log.item(row, 9) else ""

                if len(date) == 10:
                    date = date.replace('-', '')
                if len(time) == 5:
                    time = time.replace(':', '')

## Check if the log entry is after the last export date
                entry_date_time_str = f"{date} {time}"
                entry_date_time = QDateTime.fromString(entry_date_time_str, 'yyyyMMdd HHmm')
            
                if entry_date_time > last_export_date:
                    adi_data += f"<CALL:{len(call)}>{call} \n"
                    adi_data += f"<QSO_DATE:{len(date)}>{date} \n"
                    adi_data += f"<TIME_ON:{len(time)}>{time} \n"
                    adi_data += f"<BAND:{len(band)}>{band} \n"
                    adi_data += f"<FREQ:{len(freq)}>{freq} \n"
                    adi_data += f"<MODE:{len(mode)}>{mode} \n"
                    adi_data += f"<TX_PWR:{len(pwr)}>{pwr} \n"
                    adi_data += f"<RST_SENT:{len(tx)}>{tx} \n"
                    adi_data += f"<RST_RCVD:{len(rx)}>{rx} \n"
                    adi_data += "<EOR>\n\n"
          
            with open(file_name, 'w') as file:
                file.write(adi_data)
            QMessageBox.information(self, "ADIF file exported", "ADIF file exported successfully.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())







