from classes.gclass import Gclass

class Corporation(Gclass):
    obj = dict()
    lst = list()
    pos = 0
    att = ['_id', '_name', '_comments'] 

    def __init__(self, id, name, comments):
        super().__init__()
        self.id = id
        self.name = name
        self.comments = comments
        Corporation.obj[self.id] = self
        Corporation.lst.append(self.id)

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
    def comments(self):
        return self._comments

    @comments.setter
    def comments(self, value):
        self._comments = str(value)

    # O método __str__ e from_string que já tinhas estão corretos
    def __str__(self):
        return f"{self.id};{self.name};{self.comments}"

    @classmethod
    def from_string(cls, string_data):
        parts = string_data.split(';')
        return cls(int(parts[0]), parts[1], parts[2])