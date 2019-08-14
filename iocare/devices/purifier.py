import time
import collections

class Purifier(object):
    def __init__(self, data, api):
        self.api = api
        self.device_id = data['barcode']
        self.name = data['dvcNick']
        self.product_name = data['prodName']
        self.device_type = data['dvcTypeCd']
        self.device_brand = data['dvcBrandCd']
        self.refresh()

    def refresh(self):
        control_status = self.api.control_status(self)
        self.is_on = control_status['0001'] == '1'
        self.is_auto = control_status['0002'] == '1'
        self.fan_speed = control_status['0003']
        self.is_light_on = control_status['0007'] == '2'
        filters, quality, iaq = self.api.quality_status(self)
        fs = []
        for f in filters:
            fs.append({
                'name': f['filterName'],
                'life_level_pct': f['filterPer'],
                'last_changed': f['lastChangeDate'],
                'change_months': f['changeCycle']
            })
        self.filters = fs
        self.quality = {}
        if len(quality) > 0:
            q = quality[0]
            self.quality['dust_pollution'] = q['dustPollution']
            self.quality['air_volume'] = q['airVolume']
            self.quality['pollen_mode'] = q['pollenMode']
        if len(iaq) > 0:
            q = iaq[0]
            self.quality['dustpm10'] = q['dustpm10']
            self.quality['co2'] = q['co2']
            self.quality['inairquality'] = q['inairquality']

    def set_power(self, on):
        self.api.control(self, '0001', '1' if on else '0')
        self.refresh()

    def set_auto(self, auto):
        self.api.control(self, '0002', '1' if auto else '2')
        self.refresh()

    def set_fan_speed(self, speed):
        self.api.control(self, '0003', speed)
        self.refresh()

    def set_light(self, on):
        self.api.control(self, '0007', '2' if on else '0')
        self.refresh()
