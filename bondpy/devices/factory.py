
from bondpy.devices.fan import BondFanDevice

def get_bond_device(data, api):
    dev_type = data.get('dev_type')
    devices = []

    if dev_type == 'Fan':
        devices.append(BondFanDevice(data, api))
    return devices



