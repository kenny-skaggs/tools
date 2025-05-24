from dataclasses import asdict, dataclass
import json
import os


_CONFIG_FILE_PATH = '.beholder_config'


@dataclass()
class Config:
    selected_wordlist:      str
    scan_url:               str

    @classmethod
    def get_instance(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = Config(**cls._init_data())

        return cls._instance

    @classmethod
    def _init_data(cls):
        if not os.path.isfile(_CONFIG_FILE_PATH):
            return {
                'selected_wordlist': 'bobaoeu.txt',
                'scan_url': 'oeuaoeuaoeu'
            }
        
        with open(_CONFIG_FILE_PATH) as file:
            config_json = json.loads(file.read())
            return config_json
        
    def save(self):
        with open(_CONFIG_FILE_PATH, 'w') as file:
            config_str = json.dumps(asdict(self))
            file.write(config_str)
