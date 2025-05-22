from abc import ABC, abstractmethod
from typing import Iterator

from data import RequestFields


class _BaseGenerator:
    def __init__(self, url):
        self._url = url

    def get_requests(self) -> Iterator[RequestFields]:
        for value_set in self._get_value_sets():
            yield self._build_request(value_set)

    @abstractmethod
    def _get_value_sets(self) -> Iterator[tuple]:
        ...

    @abstractmethod
    def _build_request(self, value_set: tuple) -> RequestFields:
        ...



class WordlistLoader(_BaseGenerator):
    def __init__(self, url, filepath):
        super().__init__(url)
        self._filepath = filepath

    def _get_value_sets(self):
        with open(self._filepath, encoding='latin-1') as file:
            line = file.readline()
            while line:
                yield line.strip()
                line = file.readline()

        # count = 0
        # for line in lines:
        #     result.append(('auction', line))
        #     count += 1
        #     if count % 2 == 0:
        #         result.append(('weiner', 'peter'))

    def _build_request(self, value_set):
        request = RequestFields(self._url, value_set)
        request.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request.data = f'username=adserver&password={value_set}'
        return request
