from collections import defaultdict
from difflib import SequenceMatcher
from functools import partial
from enum import auto, Enum
import html
from random import choice
import sys

import PyQt6.QtCore as qtc
import PyQt6.QtGui as qtg
import PyQt6.QtWidgets as qt

import time



class ResponseWrapper:
    def __init__(self, status, content, value):
        self._status = status
        self._content = content
        self.value = str(value)

    def get_content(self):
        return self._content

    def get_status_code(self):
        return self._status


def gen_response(value):
    status = choice([200, 404, 301])
    content = choice([
        """
            first line
            <b>test 8</b>
            foo
            bar
            bqwerz
        """,
        """
            first line
            <b>test</b>
        foo
            bar test
            baoeuz
        """
    ])
    return ResponseWrapper(status, content, value)


class WorkerSignals(qtc.QObject):
    result = qtc.pyqtSignal(ResponseWrapper)


class RequestWorker(qtc.QRunnable):
    def __init__(self, value):
        super().__init__()
        self._value = value
        self.signals = WorkerSignals()

    @qtc.pyqtSlot()
    def run(self):
        time.sleep(1)
        result = gen_response(self._value)
        self.signals.result.emit(result)


class ChangeType(Enum):
    DELETE = auto()
    MODIFY = auto()
    ADD = auto()


class ChangeIndicator:
    def __init__(self, change_value, start, end):
        match change_value:
            case 'replace':
                self.color = 'yellow'
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


class ResponseCategory(qtc.QObject):
    did_update = qtc.pyqtSignal()

    def __init__(self, response: ResponseWrapper):
        super().__init__()
        self.status_code = response.get_status_code()
        self.content = response.get_content()
        self.values = []

    def setDisplay(self, display):
        self._display = display
        self._display.setText(str(self))

    def add_value(self, value):
        self.values.append(value)
        self._display.setText(str(self))
        self.did_update.emit()

    def get_count(self):
        return len(self.values)

    def __str__(self):
        return f"{self.status_code}\t\tcount: {self.get_count()}\t\tsize: {len(self.content)}"

    def __eq__(self, other):
        return self.status_code == other.status_code and self.content == other.content

    def get_map_key(self):
        return hash(str(self.status_code) + self.content)


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
        self._text_label = qt.QLabel()
        layout.addWidget(self._text_label, stretch=2)

        detail_button = qt.QPushButton("View")
        detail_button.clicked.connect(self._on_details_clicked)
        layout.addWidget(detail_button, stretch=1)

    def setText(self, text):
        self._text_label.setText(text)

    def _on_details_clicked(self):
        self.view_details.emit()

    def clear_selection(self):
        self.check_box.setChecked(False)

    def set_selected(self):
        self.check_box.setChecked(True)

    def _on_select_changed(self):
        self.did_select.emit(self.check_box.isChecked())



class ComparisonDetailWidget(qt.QWidget):
    def __init__(self, category, content, change_list):
        super().__init__()

        layout = qt.QVBoxLayout()
        layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self.status_display = qt.QLabel(f'Status Code: {category.status_code}')
        layout.addWidget(self.status_display)

        markup = self._apply_changes(content, change_list)
        markup = markup.replace('\n', '<br>')
        self.content_display = qt.QLabel(markup)
        self.content_display.setTextFormat(qtc.Qt.TextFormat.RichText)
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

        layout.addWidget(ComparisonDetailWidget(one, one_content, first_changes))
        layout.addWidget(ComparisonDetailWidget(two, two_content, second_changes))

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
        self.content_display = qt.QLabel()
        response_layout.addWidget(self.content_display)

        self.value_layout = qt.QVBoxLayout()
        self.value_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(self.value_layout, stretch=1)
        self.value_widgets = []

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
        self.content_display.setText(self._category.content)

        for w in self.value_widgets:
            self.value_layout.removeWidget(w)
        self.value_widgets = []

        for value in sorted(self._category.values):
            w = qt.QLabel(value)
            self.value_layout.addWidget(w)
            self.value_widgets.append(w)

    def closeEvent(self, _):
        self.did_close.emit()



class MainWindow(qt.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Orthrus")

        main_layout = qt.QVBoxLayout()

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

        self.count = 0
        self.threadpool = qtc.QThreadPool()
        self.threadpool.setMaxThreadCount(4)
        for i in range(200):
            worker = RequestWorker(i)
            worker.signals.result.connect(self._on_request_complete)
            self.threadpool.start(worker)

    def _on_request_complete(self, response):
        self.count += 1

        category = ResponseCategory(response)
        map_key = category.get_map_key()

        if map_key in self.category_display_map:
            self.category_display_map[map_key].add_value(response.value)
        else:
            button = ResponseCategoryDisplay(category.status_code)

            self.status_widget_map[category.status_code].append(button)
            self.response_list_layout.addWidget(button)
            self._reorder_buttons()
            category.setDisplay(button)
            category.add_value(response.value)

            button.view_details.connect(partial(self._button_clicked, category))
            button.did_select.connect(partial(self._did_select, category, button))

            self.category_display_map[map_key] = category

        self._update_progress_label(self.count, response.value)

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

    def _update_progress_label(self, num_complete, latest_value):
        self.progress_label.setText(f'{str(num_complete).rjust(10)} completed requests\t\trecent value: {latest_value}')


app = qt.QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
