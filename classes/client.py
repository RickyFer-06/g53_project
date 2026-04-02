from classes.gclass import Gclass

class Client(Gclass):
    obj = dict()
    lst = list()
    pos = 0
    sortkey = ''
    auto_number = 0
    nkey = 1

    def __init__(self, id, name, email):
        super().__init__()
        self.id = id
        self.name = name
        self.email = email

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
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
        self._email = str(value)

    def __str__(self):
        return f"{self.id};{self.name};{self.email}"

    @classmethod
    def from_string(cls, string_data):
        parts = string_data.split(';')
        return cls(int(parts[0]), parts[1], parts[2])