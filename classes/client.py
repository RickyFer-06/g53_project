from classes.gclass import Gclass

class Client(Gclass):
    obj = dict()
    lst = list()
    pos = 0

    att = ['_id', '_name', '_address'] 

    def __init__(self, id, name, address):
        super().__init__()
        self.id = id
        self.name = name
        self.address = address
        Client.obj[self.id] = self
        Client.lst.append(self.id)

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
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        self._address = str(value)

    def __str__(self):
        return f"{self.id};{self.name};{self.address}"

    @classmethod
    def from_string(cls, string_data):
        parts = string_data.split(';')
        return cls(int(parts[0]), parts[1], parts[2])