# -*- coding: utf-8 -*-
# MyJD
# Project by https://github.com/rix1337

import configparser


class Config(object):
    _DEFAULT_CONFIG = {
        'MyJD': [
            ("myjd_user", "str", ""),
            ("myjd_pass", "str", ""),
            ("myjd_device", "str", ""),
            ("port", "int", "8080"),
        ],
        'Auth': [
            ("auth_user", "str", ""),
            ("auth_hash", "str", ""),
        ],
    }
    __config__ = []

    def __init__(self, section, configfile):
        self._configfile = configfile
        self._section = section
        self._config = configparser.RawConfigParser()
        try:
            self._config.read(self._configfile)
            self._config.has_section(
                self._section) or self._set_default_config(self._section)
            self.__config__ = self._read_config(self._section)
        except configparser.DuplicateSectionError:
            print(u'Duplicate section in config file.')
            raise
        except:
            print(u'Unknown error in config file.')
            raise

    def _set_default_config(self, section):
        self._config.add_section(section)
        for (key, key_type, value) in self._DEFAULT_CONFIG[section]:
            self._config.set(section, key, value)
        with open(self._configfile, 'w') as configfile:
            self._config.write(configfile)

    def _set_to_config(self, section, key, value):
        self._config.set(section, key, value)
        with open(self._configfile, 'w') as configfile:
            self._config.write(configfile)

    def _read_config(self, section):
        return [(key, '', self._config.get(section, key)) for key in self._config.options(section)]

    def _get_from_config(self, scope, key):
        res = [param[2] for param in scope if param[0] == key]
        if not res:
            res = [param[2]
                   for param in self._DEFAULT_CONFIG[self._section] if param[0] == key]
        if [param for param in self._DEFAULT_CONFIG[self._section] if param[0] == key and param[1] == 'bool']:
            return True if len(res) and res[0].strip('\'"').lower() == 'true' else False
        else:
            return res[0].strip('\'"') if len(res) > 0 else False

    def save(self, key, value):
        self._set_to_config(self._section, key, value)
        return

    def get(self, key):
        return self._get_from_config(self.__config__, key)
