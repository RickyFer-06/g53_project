from classes.gclass import Gclass

class Broker(Gclass):
    obj = dict()
    lst = list()
    pos = 0
    sortkey = ''
    auto_number = 0
    nkey = 1

    def __init__(self, id, name, license_number, corporation_id):
        super().__init__()
        self.id = id
        self.name = name
        self.license_number = license_number
        self.corporation_id = corporation_id

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = int(value)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = str(value)

    @property
    def license_number(self):
        return self._license_number

    @license_number.setter
    def license_number(self, value):
        self._license_number = int(value)

    @property
    def corporation_id(self):
        return self._corporation_id

    @corporation_id.setter
    def corporation_id(self, value):
        self._corporation_id = int(value)

    def __str__(self):
        return f"{self.id};{self.name};{self.license_number};{self.corporation_id}"

    @classmethod
    def from_string(cls, string_data):
        parts = string_data.split(';')
        return cls(int(parts[0]), parts[1], int(parts[2]), int(parts[3]))