from abc import ABC
from dataclasses import dataclass

from bs4 import BeautifulSoup, element

from data import RequestFields


class RequestModifier(ABC):
    def modify(self, fields: RequestFields):
        pass


class ResponseModifier(ABC):
    def modify(self, info):
        pass


class SoupStrainer:
    def clean(self, content):
        return content
        # soup = BeautifulSoup(content, 'lxml')

        # to_remove = []
        # for i, child in enumerate(soup.body.children):

        #     if isinstance(child, element.Comment):
        #         to_remove.append(child.next_sibling)
        #         to_remove.append(child)
        #     elif isinstance(child, element.Tag) and child.name == 'script':
        #         to_remove.append(child)
        #         break

        # for tag in to_remove:
        #     tag.extract()

        # return str(soup)

class ForwardedForSpoofer(RequestModifier):
    def __init__(self):
        super().__init__()
        self._count = 1

    def modify(self, fields: RequestFields):
        self._count += 1
        if self._count > 210:
            self._count = 1

        spoof_ip = f'147.89.201.{self._count}'
        fields.headers['X-Forwarded-For'] = spoof_ip
