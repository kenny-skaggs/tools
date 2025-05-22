from base64 import b64encode
import hashlib

import requests

from data import RequestFields, ResponseInfo


class Requestor:
    def __init__(self, url):
        self._url = url
        self._modifiers = []

    def make_request(self, request: RequestFields):
        response = requests.post(
            request.url,
            headers=request.headers,
            data=request.data
        )

        return self._build_response_info(response, request.value_set)

    def _build_response_info(self, response, value):
        result = ResponseInfo()
        result.status_code = response.status_code
        result.content = response.text
        result.value = value
        return result
    
    def _md5(self, value: str):
        hash = hashlib.md5(value.encode('utf8'))
        return hash.hexdigest()
    
    def _b64_encode(self, value: str):
        b64_bytes = b64encode(value.encode('utf8'))
        return b64_bytes.decode('utf8')
