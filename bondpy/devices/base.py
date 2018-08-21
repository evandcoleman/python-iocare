import time

class BondCommand(object):
    def __init__(self, data):
        self.id = data.get('device_property_command_id')
        self.name = data.get('command_type')

    def command_id(self):
        return self.id

    def name(self):
        return self.name

class BondDevice(object):
    def __init__(self, data, api):
        self.api = api
        self.data = data
        self.obj_id = data[0].get('device_property_id')
        self.obj_name = data[0].get('location_type') + ' ' + data[0].get('device_type')
        self.dev_type = data[0].get('device_type')
        self.commands = list(map(lambda x: BondCommand(x), data))

    def name(self):
        return self.obj_name

    def commands(self):
        return self.commands

    def device_type(self):
        return self.dev_type

    def object_id(self):
        return self.obj_id
