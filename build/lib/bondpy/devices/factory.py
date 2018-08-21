
from bondpy.devices.fan import BondFanDevice

def get_bond_device(data, api):
    dev_type = data[0].get('device_type')
    devices = []

    if dev_type == 'Fan':
        devices.append(BondFanDevice(data, api))
    return devices



