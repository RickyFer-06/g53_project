from classes.gclass import Gclass
import datetime

class Trade(Gclass):
    obj = dict()
    lst = list()
    pos = 0
    att = ['_id', '_broker_id', '_client_id', '_name', '_date', '_amount']

    def __init__(self, id, broker_id, client_id, name, date, amount):
        super().__init__()
        self.id = id
        self.broker_id = broker_id
        self.client_id = client_id
        self.name = name
        self.date = date
        self.amount = amount
        Trade.obj[self.id] = self
        Trade.lst.append(self.id)

    @property
    def id(self): return self._id
    @id.setter
    def id(self, value): self._id = int(value)

    @property
    def broker_id(self): return self._broker_id
    @broker_id.setter
    def broker_id(self, value): self._broker_id = int(value)

    @property
    def client_id(self): return self._client_id
    @client_id.setter
    def client_id(self, value): self._client_id = int(value)

    @property
    def name(self): return self._name
    @name.setter
    def name(self, value): self._name = str(value)

    @property
    def date(self): return self._date
    @date.setter
    def date(self, value):
        if isinstance(value, datetime.date):
            self._date = value
        else:
            self._date = datetime.date.fromisoformat(str(value))

    @property
    def amount(self): return self._amount
    @amount.setter
    def amount(self, value): self._amount = float(value)

    def __str__(self):
        return f"{self.id};{self.broker_id};{self.client_id};{self.name};{self.date};{self.amount}"

    @classmethod
    def from_string(cls, string_data):
        parts = string_data.split(';')
        return cls(int(parts[0]), int(parts[1]), int(parts[2]), parts[3], parts[4], float(parts[5]))