from typing import List

import PyQt6.QtCore as qtc
import PyQt6.QtGui as qtg
import PyQt6.QtWidgets as qt

from data import ResponseCategory
from project import Config


class InitialWindow(qt.QMainWindow):
    new_selected = qtc.pyqtSignal()
    load_selected = qtc.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Beholder - Start')

        layout = qt.QVBoxLayout()

        new_btn = qt.QPushButton('New Scan')
        new_btn.clicked.connect(self.new_selected)
        layout.addWidget(new_btn)

        load_btn = qt.QPushButton('Load Scan')
        load_btn.clicked.connect(self._on_load_results)
        layout.addWidget(load_btn)

        container = qt.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._file_dialog = None

    def _on_load_results(self):
        filters = ["Beholder Collections (*.bhldr)"]

        self._file_dialog = qt.QFileDialog()
        self._file_dialog.setNameFilters(filters)
        self._file_dialog.fileSelected.connect(self.load_selected)
        self._file_dialog.show()


class FuzzValueListWidget(qt.QVBoxLayout):
    def __init__(self):
        super().__init__()
        self._value_widgets = []

        self.list_widget = qt.QWidget()
        self._list_layout = qt.QVBoxLayout()

        self._list_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)
        self.list_widget.setLayout(self._list_layout)

        self.list_scroll = qt.QScrollArea()
        self.list_scroll.setWidget(self.list_widget)
        self.list_scroll.setWidgetResizable(True)
        self.addWidget(self.list_scroll)

    def display_values(self, value_list):
        for w in self._value_widgets:
            self._list_layout.removeWidget(w)

        for value_set in value_list:
            label = qt.QLabel(str(value_set))
            self._list_layout.addWidget(label)
            self._value_widgets.append(label)


class HtmlView(qt.QScrollArea):
    def __init__(self):
        super().__init__()

        self.setWidgetResizable(True)

        self._content_label = qt.QLabel()
        self._content_label.setAlignment(qtc.Qt.AlignmentFlag.AlignTop | qtc.Qt.AlignmentFlag.AlignLeft)
        self._content_label.setWordWrap(True)
        self.setWidget(self._content_label)

    def setRichTextFormat(self):
        self._content_label.setTextFormat(qtc.Qt.TextFormat.RichText)

    def setText(self, text):
        self._content_label.setText(text.replace('\n', '<br>'))


class ResponseCategoryDisplay(qt.QWidget):
    view_details = qtc.pyqtSignal()
    did_select = qtc.pyqtSignal(bool)

    def __init__(self, status_code):
        super().__init__()
        self.status_code = status_code

        layout = qt.QHBoxLayout()
        self.setLayout(layout)

        self.check_box = qt.QCheckBox()
        self.check_box.stateChanged.connect(self._on_select_changed)
        layout.addWidget(self.check_box, stretch=1)

        self._status_label = qt.QLabel()
        layout.addWidget(self._status_label, stretch=1)

        self._count_label = qt.QLabel()
        layout.addWidget(self._count_label, stretch=1)

        self._size_label = qt.QLabel()
        layout.addWidget(self._size_label, stretch=1)

        detail_button = qt.QPushButton("View")
        detail_button.clicked.connect(self._on_details_clicked)
        layout.addWidget(detail_button, stretch=1)

    def setResponse(self, category: ResponseCategory):
        self._status_label.setText(str(category.status_code))
        self._count_label.setText(f'count: {category.get_count()}')
        self._size_label.setText(f'size: {len(category.content)}')

    def _on_details_clicked(self):
        self.view_details.emit()

    def clear_selection(self):
        self.check_box.setChecked(False)

    def set_selected(self):
        self.check_box.setChecked(True)

    def _on_select_changed(self):
        self.did_select.emit(self.check_box.isChecked())


class StrainerManagement(qt.QMainWindow):
    def __init__(self, strainer_list):
        super().__init__()
        self.setWindowTitle('Strainer')
        self.setMinimumSize(qtc.QSize(400, 200))

        main_layout = qt.QHBoxLayout()

        list_widget = qt.QListWidget()
        for name in strainer_list:
            list_widget.addItem(name)
        main_layout.addWidget(list_widget, stretch=2)

        button_layout = qt.QVBoxLayout()
        button_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)
        add_btn = qt.QPushButton('Add')
        add_btn.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(add_btn)
        edit_btn = qt.QPushButton('Edit')
        button_layout.addWidget(edit_btn)
        remove_btn = qt.QPushButton('Remove')
        button_layout.addWidget(remove_btn)
        main_layout.addLayout(button_layout, stretch=1)

        container = qt.QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self._edit_window = None

    def _on_add_clicked(self):
        self._edit_window = StrainerEditing()
        self._edit_window.show()


class StrainerEditing(qt.QMainWindow):
    def __init__(self):
        super().__init__()

        main_layout = qt.QVBoxLayout()

        self._text_edit = qt.QPlainTextEdit()
        self._text_edit.setTabStopDistance(30)
        main_layout.addWidget(self._text_edit, stretch=2)

        button_layout = qt.QHBoxLayout()
        button_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignRight)
        save_btn = qt.QPushButton('Save')
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)
        cancel_btn = qt.QPushButton('Cancel')
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout, stretch=1)

        container = qt.QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
    def _on_save(self):
        new_strainer = self._text_edit.toPlainText()

        scope = {'soup': 5}
        print('sending ', scope['soup'])
        exec(new_strainer, globals={}, locals=scope)
        print('new soup: ', scope['soup'])


class ScanConfig(qt.QMainWindow):
    clicked_start = qtc.pyqtSignal()

    def __init__(self):
        super().__init__()
        config = Config.get_instance()

        self._selected_file = config.selected_wordlist

        main_layout = qt.QVBoxLayout()
        main_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)

        url_layout = self._build_url_layout(config.scan_url)
        main_layout.addLayout(url_layout)

        wordlist_layout = self._build_wordlist_layout()
        main_layout.addLayout(wordlist_layout)

        button_layout = qt.QHBoxLayout()
        button_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignRight | qtc.Qt.AlignmentFlag.AlignBottom)
        scan_btn = qt.QPushButton('Start')
        scan_btn.clicked.connect(self._on_start_clicked)
        button_layout.addWidget(scan_btn)
        main_layout.addLayout(button_layout, stretch=1)

        container = qt.QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.setMinimumSize(qtc.QSize(800, 300))

    def _build_url_layout(self, default_url):
        layout = qt.QHBoxLayout()

        label = qt.QLabel('url:')
        layout.addWidget(label, stretch=1)

        self._url_input = qt.QLineEdit(default_url)
        layout.addWidget(self._url_input, stretch=4)

        return layout

    def _build_wordlist_layout(self):
        layout = qt.QHBoxLayout()

        self._wordlist_label = qt.QLabel(self._selected_file)
        layout.addWidget(self._wordlist_label, stretch=4)

        btn = qt.QPushButton('Open')
        btn.clicked.connect(self._select_wordlist_file)
        layout.addWidget(btn, stretch=1)

        return layout
    
    def _select_wordlist_file(self):
        self._file_dialog = qt.QFileDialog()
        self._file_dialog.fileSelected.connect(self._use_selected_file)
        self._file_dialog.setDirectory('/usr/share/wordlists/')
        self._file_dialog.show()

    def _use_selected_file(self, wordlist_path):
        self._wordlist_label.setText(wordlist_path)
        self._selected_file = wordlist_path

    def _on_start_clicked(self):
        config = Config.get_instance()
        config.scan_url = self.scan_url
        config.selected_wordlist = self.wordlist_path

        self.clicked_start.emit()

    @property
    def scan_url(self):
        return self._url_input.text()
    
    @property
    def wordlist_path(self):
        return self._selected_file
