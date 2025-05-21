from dataclasses import dataclass
import json
from typing import Dict, List

import PyQt6.QtCore as qtc


class RequestFields:
    def __init__(self, url):
        self.url = url
        self.headers = {}
        self.data = ""


@dataclass()
class ResponseInfo:
    status_code:        int             = None
    response_time_ms:   int             = None
    headers:            Dict[str, str]  = None
    content:            str             = None

    value:              str             = None

    def as_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, d):
        result = cls()
        result.__dict__ = d
        return result

    def __str__(self):
        return f'{self.status_code}, time: {self.response_time_ms}\n{self.headers}\n{self.content}\n---'


class Serialization:
    @classmethod
    def save_to_file(cls, response_list: List[ResponseInfo], file_path):
        json_data = [response.as_dict() for response in response_list]

        with open(file_path, 'w') as file:
            file.write(json.dumps(json_data))

    @classmethod
    def load_from_file(cls, file_path) -> List[ResponseInfo]:
        with open(file_path) as file:
            data_str = file.read()
            
        json_data = json.loads(data_str)
        return [ResponseInfo.from_dict(entry) for entry in json_data]
    

class ResponseCategory(qtc.QObject):
    did_update = qtc.pyqtSignal()

    def __init__(self, response):
        super().__init__()
        self.status_code = response.status_code
        self.content = response.content
        self.values = []

    def setDisplay(self, display):
        self._display = display
        self._display.setResponse(self)

    def add_value(self, value):
        self.values.append(value)
        self._display.setResponse(self)
        self.did_update.emit()

    def get_count(self):
        return len(self.values)

    def __eq__(self, other):
        return self.status_code == other.status_code and self.content == other.content

    def get_map_key(self):
        return hash(str(self.status_code) + self.content)
