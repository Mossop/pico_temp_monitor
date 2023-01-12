import json


class Config:
    def __init__(self):
        fd = open("config.json")
        self._config = json.load(fd)
        fd.close()

    def __getattr__(self, name):
        if name == "password":
            if "password" in self._config:
                return self._config
            else:
                return ""
        return self._config[name]

CONFIG = Config()
