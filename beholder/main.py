from collections import defaultdict
from difflib import SequenceMatcher
from functools import partial
from enum import auto, Enum
import html
import sys

import PyQt6.QtCore as qtc
import PyQt6.QtGui as qtg
import PyQt6.QtWidgets as qt

from data import ResponseInfo, ResponseCategory, Serialization
from networking import Requestor
import ui
from value_generation import FileLoader, TokenRange

import time


THREAD_COUNT = 8
DEFAULT_URL = 'https://0abe00d90311872d82e4e2fa00ec0049.web-security-academy.net/login'
FUZZ_FILE_PATH = 'bob.txt'


class WorkerSignals(qtc.QObject):
    result = qtc.pyqtSignal(ResponseInfo)


class RequestWorker(qtc.QRunnable):
    def __init__(self, value_set, requestor: Requestor):
        super().__init__()
        self._value_set = value_set
        self.signals = WorkerSignals()
        self._requestor = requestor

    @qtc.pyqtSlot()
    def run(self):
        time.sleep(0.2)
        result = self._requestor.make_request(self._value_set)
        self.signals.result.emit(result)


class ChangeType(Enum):
    DELETE = auto()
    MODIFY = auto()
    ADD = auto()


class ChangeIndicator:
    def __init__(self, change_value, start, end):
        match change_value:
            case 'replace':
                self.color = '#505000'
            case 'delete':
                self.color = 'red'
            case 'insert':
                self.color = 'green'

        self.start = start
        self.end = end
        self.length = end - start

    def __str__(self):
        return f'{self.color} {self.start} {self.end} {self.length}'

    def __repr__(self):
        return self.__str__()



class ComparisonDetailWidget(qt.QWidget):
    def __init__(self, category, content, change_list):
        super().__init__()

        layout = qt.QVBoxLayout()
        layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self.status_display = qt.QLabel(f'Status Code: {category.status_code}')
        layout.addWidget(self.status_display)

        markup = self._apply_changes(content, change_list)

        self.content_display = ui.HtmlView()
        self.content_display.setRichTextFormat()
        self.content_display.setText(markup)
        layout.addWidget(self.content_display)

    def _apply_changes(self, text, change_list):
        offset = 0

        for change in change_list:
            span_start = f'<span style="background-color: {change.color}">'
            text = text[: change.start + offset] + span_start + text[change.start + offset :]
            offset += len(span_start)

            span_end = '</span>'
            text = text[: change.end + offset] + span_end + text[change.end + offset :]
            offset += len(span_end)

        return text

    def get_scroll_bars(self):
        return self.content_display.verticalScrollBar(), self.content_display.horizontalScrollBar()


class ComparisonWindow(qt.QMainWindow):
    did_close = qtc.pyqtSignal()

    def __init__(self, one, two):
        super().__init__()

        one_content = html.escape(one.content)
        two_content = html.escape(two.content)

        matcher = SequenceMatcher(None, one_content, two_content, autojunk=False)
        first_changes = []
        second_changes = []
        for tag, a1, a2, b1, b2 in matcher.get_opcodes():
            if a1 == a2:
                second_changes.append(ChangeIndicator(tag, b1, b2))
            elif b1 == b2:
                first_changes.append(ChangeIndicator(tag, a1, a2))
            elif tag == 'replace':
                first_changes.append(ChangeIndicator(tag, a1, a2))
                second_changes.append(ChangeIndicator(tag, b1, b2))
            else:
                assert(tag == 'equal')

        self.setWindowTitle('Comparison')

        layout = qt.QHBoxLayout()

        one_window = ComparisonDetailWidget(one, one_content, first_changes)
        two_window = ComparisonDetailWidget(two, two_content, second_changes)
        layout.addWidget(one_window)
        layout.addWidget(two_window)

        v1_scroll, h1_scroll = one_window.get_scroll_bars()
        v2_scroll, h2_scroll = two_window.get_scroll_bars()
        v1_scroll.valueChanged.connect(v2_scroll.setValue)
        h1_scroll.valueChanged.connect(h2_scroll.setValue)

        container = qt.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setMinimumSize(qtc.QSize(1200, 700))

        self._category = None


class DetailsWindow(qt.QMainWindow):
    did_close = qtc.pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle('Details')

        main_layout = qt.QHBoxLayout()

        response_layout = qt.QVBoxLayout()
        response_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(response_layout, stretch=2)

        self.count_display = qt.QLabel()
        response_layout.addWidget(self.count_display)
        self.status_display = qt.QLabel()
        response_layout.addWidget(self.status_display)
        
        self.content_display = ui.HtmlView()  # todo: not display all content for some reason
        response_layout.addWidget(self.content_display)

        self.value_layout = ui.FuzzValueListWidget()
        main_layout.addLayout(self.value_layout, stretch=1)

        container = qt.QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.setMinimumSize(qtc.QSize(800, 700))

        self._category = None

    def set_category(self, category: ResponseCategory):
        if self._category:
            self._category.did_update.disconnect(self._on_category_update)

        category.did_update.connect(self._on_category_update)

        self._category = category
        self._on_category_update()

    def _on_category_update(self):
        self.count_display.setText(f'Count: {self._category.get_count()}')
        self.status_display.setText(f'Status Code: {self._category.status_code}')
        
        new_content = html.escape(self._category.content)
        self.content_display.setText(new_content)

        self.value_layout.display_values(self._category.values)

    def closeEvent(self, _):
        self.did_close.emit()



class MainWindow(qt.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Beholder")

        main_layout = qt.QVBoxLayout()

        self._add_scan_controls(main_layout)

        status_layout = qt.QHBoxLayout()
        main_layout.addLayout(status_layout)

        self.progress_label = qt.QLabel()
        status_layout.addWidget(self.progress_label)

        self.response_list_layout = qt.QVBoxLayout()
        self.response_list_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(self.response_list_layout, stretch=2)

        bottom_bar = qt.QHBoxLayout()
        self.compare_button = qt.QPushButton('Compare')
        self.compare_button.setDisabled(True)
        self.compare_button.clicked.connect(self._display_comparison)
        bottom_bar.addWidget(self.compare_button)
        main_layout.addLayout(bottom_bar, stretch=1)

        container = qt.QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.setMinimumSize(qtc.QSize(600, 800))

        self.category_display_map = dict()
        self.status_widget_map = defaultdict(list)

        self.detail_window = None

        self.selected_categories = []
        self.raw_results = []

        self._setup_menu()

        self._total_values = 0

    def _setup_menu(self):
        save_action = qtg.QAction('Save Results', self)
        save_action.triggered.connect(self._on_menu_save_selected)
        strainer_action = qtg.QAction('Strainers...', self)
        strainer_action.triggered.connect(self._on_menu_strainer_selected)

        menu = self.menuBar()
        file_menu = menu.addMenu('File')
        file_menu.addAction(save_action)
        file_menu.addAction(strainer_action)

    def _add_scan_controls(self, layout):
        control_layout = qt.QHBoxLayout()
        layout.addLayout(control_layout)

        self.url_input = qt.QLineEdit(DEFAULT_URL)
        control_layout.addWidget(self.url_input)

        start_button = qt.QPushButton('Start Scan')
        start_button.clicked.connect(self._begin_scanning)
        control_layout.addWidget(start_button)

    def _begin_scanning(self):
        requestor = Requestor(self.url_input.text())

        self.threadpool = qtc.QThreadPool()
        self.threadpool.setMaxThreadCount(THREAD_COUNT)

        test_file = FUZZ_FILE_PATH
        # loader = FileLoader(test_file)
        loader = TokenRange()
        for val_set in loader.get_value_sets():
            self._total_values += 1
            worker = RequestWorker(val_set, requestor)
            worker.signals.result.connect(self._process_response)
            self.threadpool.start(worker)

    def load_results(self, response_list):
        for response in response_list:
            self._process_response(response)

    def _process_response(self, response):
        self.raw_results.append(response)

        category = ResponseCategory(response)
        map_key = category.get_map_key()

        if map_key in self.category_display_map:
            self.category_display_map[map_key].add_value(response.value)
        else:
            button = ui.ResponseCategoryDisplay(category.status_code)

            self.status_widget_map[category.status_code].append(button)
            self.response_list_layout.addWidget(button)
            self._reorder_buttons()
            category.setDisplay(button)
            category.add_value(response.value)

            button.view_details.connect(partial(self._button_clicked, category))
            button.did_select.connect(partial(self._did_select, category, button))

            self.category_display_map[map_key] = category

        self._update_progress_label(response.value)

    def _button_clicked(self, category):
        if not self.detail_window:
            self.detail_window = DetailsWindow()
            self.detail_window.show()
            self.detail_window.did_close.connect(self._on_details_closed)

        self.detail_window.set_category(category)

    def _display_comparison(self):
        self.compare_window = ComparisonWindow(*self.selected_categories)
        self.compare_window.show()

    def _reorder_buttons(self):
        for w_list in self.status_widget_map.values():
            for w in w_list:
                self.response_list_layout.removeWidget(w)

        for status in sorted(self.status_widget_map.keys()):
            for w in self.status_widget_map[status]:
                self.response_list_layout.addWidget(w)

    def _on_details_closed(self):
        self.detail_window = None

    def _clear_selected(self):
        for w_list in self.status_widget_map.values():
            for w in w_list:
                w.clear_selection()

    def _did_select(self, category, display, should_add):
        if should_add:
            if category in self.selected_categories:
                return

            if len(self.selected_categories) >= 2:
                self._clear_selected()
                self.selected_categories = []
                display.set_selected()

            self.selected_categories.append(category)
        elif category in self.selected_categories:
            self.selected_categories = [cat for cat in self.selected_categories if cat != category]

        self.compare_button.setDisabled(len(self.selected_categories) != 2)

    def _update_progress_label(self, latest_value):
        if self._total_values == 0:
            return
        
        complete_count = len(self.raw_results)
        percent_complete = round(complete_count / self._total_values * 100, 1)
        self.progress_label.setText(
            f'{complete_count} '
            f'completed requests ({percent_complete}%)'
            f'\t\trecent value: {latest_value}'
        )

    def _on_menu_save_selected(self):
        self._file_dialog = qt.QFileDialog()
        self._file_dialog.setAcceptMode(qt.QFileDialog.AcceptMode.AcceptSave)
        filters = ["Beholder Collections (*.bhldr)"]
        self._file_dialog.setNameFilters(filters)
        self._file_dialog.setDefaultSuffix('bhldr')
        self._file_dialog.fileSelected.connect(self._on_save_results)
        self._file_dialog.show()

    def _on_menu_strainer_selected(self):
        self._strainer_dialog = ui.StrainerManagement(['one', 'two', 'three'])
        self._strainer_dialog.show()

    def _on_save_results(self, file_path):
        Serialization.save_to_file(self.raw_results, file_path)


class MainControllor(qtc.QObject):
    def __init__(self):
        super().__init__()
        self._scan_window = None

        self._initial_window = ui.InitialWindow()
        self._initial_window.new_selected.connect(self.open_scan_window)
        self._initial_window.load_selected.connect(self.load_file)
        self._initial_window.show()

    def open_scan_window(self):
        self._initial_window.close()

        self._scan_window = MainWindow()
        self._scan_window.show()

    def load_file(self, file_path):
        response_list = Serialization.load_from_file(file_path)
        self.open_scan_window()
        self._scan_window.load_results(response_list)


app = qt.QApplication(sys.argv)
controller = MainControllor()
app.exec()
