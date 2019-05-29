from pprint import pprint
import math

class RegisterComparison:

    def __init__(self, meter, register_id, match_fixed=False):
        self.meter = meter
        self.register_id = register_id
        self.portal_rows = []
        self.dynamics_rows = []
        self.in_portal = False
        self.in_dynamics = False
        self.match_fixed = match_fixed
        self.action = None

    def add_dynamics_row(self, row):
        self.dynamics_rows.append(row)

    def add_portal_row(self, row):
        self.portal_rows.append(row)

    def update_counts(self):
        self.in_portal = True if self.portal_rows else False
        self.in_dynamics = True if self.dynamics_rows else False

    def output_comparison_rows(self):
        output_records = {
            'comparison': [],
            'create': [],
            'update_tpr': [],
            'update_leading_0': [],
            'duplicate_portal_registers': [],
        }
        max_length = max(len(self.dynamics_rows), len(self.portal_rows))
        for i in range(max_length):
            record = {
                'mpan': self.meter.mpan.mpan,
                'serial_no': self.meter.serial_no,
                'register_id': self.register_id,
                # 'mpan_meter_action': self.meter.mpan.meter_action,
                # 'meter_action': self.meter.meter_action,
                # 'meter_register_action': self.meter.register_action,
                # 'register_action': self.action,
            }
            try:
                for key, value in self.dynamics_rows[i].items():
                    record[f'{key}_d'] = value
            except IndexError:
                pass
            try:
                for key, value in self.portal_rows[i].items():
                    record[f'{key}_p'] = value
            except IndexError:
                pass
            if self.meter.mpan.in_portal and not self.meter.mpan.in_dynamics:
                use_case = 'MPAN in portal but not in Dynamics'
            elif self.meter.mpan.in_dynamics and not self.meter.mpan.in_portal:
                use_case = 'MPAN in Dynamics but not in portal'
            elif self.meter.in_portal and not self.meter.in_dynamics:
                use_case = 'Meter in portal but not in Dynamics'
            elif self.meter.in_dynamics and not self.meter.in_portal:
                use_case = 'Meter in Dynamics but not in portal'
            elif self.in_portal and not self.in_dynamics:
                use_case = 'Register in portal but not in Dynamics'
            elif self.in_dynamics and not self.in_portal:
                use_case = 'Register in Dynamics but not in portal'
            else:
                use_case = 'Match'
            if self.meter.mpan.no_s15:
                use_case = f'No S15 {use_case}'
            record['use_case'] = use_case
            dynamics_meter_count = self.meter.mpan.dynamics_meter_count
            portal_meter_count = self.meter.mpan.portal_meter_count
            meter_match_count = self.meter.mpan.meter_match_count
            dynamics_register_count = self.meter.dynamics_register_count
            portal_register_count = self.meter.portal_register_count
            register_match_count = self.meter.register_match_count
            record[
                'mpan_meter_count'] = f'{dynamics_meter_count} meters in Dynamics, {portal_meter_count} meters in portal ({meter_match_count} matches)'
            record[
                'meter_register_count'] = f'{dynamics_register_count} registers in Dynamics, {portal_register_count} registers in portal ({register_match_count} matches)'
            output_records['comparison'].append(record)
            if dynamics_meter_count == portal_meter_count == meter_match_count:
                if portal_register_count == register_match_count:
                    if self.in_dynamics and self.in_portal:
                        if len(self.portal_rows) > 1:
                            output_records['duplicate_portal_registers'].append(self.dynamics_rows[i])
                        elif self.match_fixed:
                            output_records['update_leading_0'].append(self.update_register_id())
                        elif self.dynamics_rows[0]['d4e_timepatternregime'] != self.portal_rows[0][
                            'pattern']:
                            output_records['update_tpr'].append(self.update_tpr())
                    elif self.in_dynamics and not self.in_portal:
                        output_records['create'].append(self.create_in_portal())
        return output_records

    # def determine_action(self):
    #     if self.in_portal and self.in_dynamics:
    #         if len(self.portal_rows) > 1:
    #             self.action = 'investigate duplicate'

    #         elif self.dynamics_rows[0]['d4e_timepatternregime'] != self.portal_rows[0][
    #             'pattern']:
    #             self.action = 'update tpr in portal with tpr from dynamics'
    #         else:
    #             'do nothing'
    #     elif self.in_portal and not self.in_dynamics:
    #         self.action = 'deactivate in portal'
    #     elif self.in_dynamics and not self.in_portal:
    #         self.action = 'create in portal'

    def update_tpr(self):
        record = {
            'id': self.portal_rows[0]['id'],
            'register_id': self.portal_rows[0]['register_id'],
            'multiplier': self.portal_rows[0]['multiplier'],
            'digits': self.portal_rows[0]['digits'],
            'is_reading': self.portal_rows[0]['is_reading'],
            'meter_type_id': self.portal_rows[0]['meter_type_id'],
            'serial_number_id': self.portal_rows[0]['serial_number_id'],
            'time_pattern_regime_id': self.dynamics_rows[0]['portal_tpr_id'],
            'eac': self.portal_rows[0]['eac'],
        }
        return record

    def update_register_id(self):
        record = {
            'id': self.portal_rows[0]['id'],
            'register_id': self.dynamics_rows[0]['d4e_meterregisterid'],
            'multiplier': self.portal_rows[0]['multiplier'],
            'digits': self.portal_rows[0]['digits'],
            'is_reading': self.portal_rows[0]['is_reading'],
            'meter_type_id': self.portal_rows[0]['meter_type_id'],
            'serial_number_id': self.portal_rows[0]['serial_number_id'],
            'time_pattern_regime_id': self.portal_rows[0]['time_pattern_regime_id'],
            'eac': self.portal_rows[0]['eac'],
        }

    def create_in_portal(self):
        eac = '0' if math.isnan(self.dynamics_rows[0]['d4e_estimatedusage']) else int(self.dynamics_rows[0]['d4e_estimatedusage'])
        try:
            tpr = self.dynamics_rows[0]['d4e_timepatternregime'].zfill(5)
        except AttributeError:
            print('here')
            pprint(self.dynamics_rows)
        record = {
            'electricity_mpan': self.meter.mpan.mpan,
            'serial_number': self.meter.serial_no,
            'register_id': self.dynamics_rows[0]['d4e_meterregisterid'],
            'multiplier': 1,
            'meter_type': self.dynamics_rows[0]['d4e_metertype'],
            'digits': 5,
            'time_pattern_regime': tpr,
            'is_reading': False,
            'eac': eac
        }
        return record


class MeterComparison:

    def __init__(self, mpan, serial_no, match_fixed=False):
        self.mpan = mpan
        self.match_fixed = match_fixed
        self.serial_no = serial_no
        self.registers = {}
        self.portal_register_count = None
        self.dynamics_register_count = None
        self.register_match_count = None
        self.in_portal = False
        self.in_dynamics = False
        self.meter_action = None
        self.register_action = None

    def update_counts(self):
        self.portal_register_count = len(
            [register for register, records in self.registers.items() if records.portal_rows])
        self.dynamics_register_count = len(
            [register for register, records in self.registers.items() if records.dynamics_rows])
        self.register_match_count = len(
            [register for register, records in self.registers.items() if
             records.dynamics_rows and records.portal_rows])
        self.in_portal = True if self.portal_register_count else False
        self.in_dynamics = True if self.dynamics_register_count else False

    # def determine_register_action(self):
    #     if self.portal_register_count == 1 and self.dynamics_register_count == 1:
    #         if self.register_match_count == 1:
    #             self.register_action = 'do nothing'
    #         elif self.register_match_count == 0:
    #             self.register_action = 'overwrite portal register with data from dynamics register'
    #     elif self.portal_register_count == self.dynamics_register_count:
    #         if self.portal_register_count == self.register_match_count:
    #             self.register_action = 'do nothing'
    #         elif self.register_match_count < self.portal_register_count:
    #             self.register_action = 'investigate mismatched registers'
    #     elif self.portal_register_count < self.dynamics_register_count:
    #         self.register_action = 'create missing registers in portal'
    #     elif self.portal_register_count > self.dynamics_register_count:
    #         self.register_action = 'investigate extra registers in portal'
    #
    # def determine_action(self):
    #     if self.in_portal and self.in_dynamics:
    #         if self.match_fixed:
    #             self.meter_action = 'update register id for leading 0 issue'
    #         else:
    #             'do nothing'
    #     elif self.in_portal and not self.in_dynamics:
    #         self.meter_action = 'deactivate in portal'
    #     elif self.in_dynamics and not self.in_portal:
    #         self.meter_action = 'create in portal'

    def create_in_portal(self):
        'electricity_mpan, serial_number'
        record = {
            'electricity_mpan': self.mpan.mpan,
            'serial_number': self.serial_no,
        }

    def update_serial_no(self):
        record = {
            # 'id': self.,
            'serial_number': None,
            'mpan_meter_group_id': None,
        }


class MpanComparison:

    def __init__(self, mpan):
        self.mpan = mpan
        self.meters = {}
        self.portal_meter_count = 0
        self.dynamics_meter_count = 0
        self.meter_match_count = 0
        self.no_s15 = False
        self.in_portal = False
        self.in_dynamics = False
        self.meter_action = None

    def check_leading_0s(self, string1, string2):
        if f'0{string1}' == string2 or f'0{string2}' == string1:
            return True
        else:
            return False

    def process_dynamics_row(self, row):
        serial_no = row['d4e_serial_number']
        register = row['d4e_meterregisterid']
        serial_no = serial_no.upper() if serial_no else serial_no
        register = register.upper() if register else register
        if not register or not serial_no or not row['d4e_timepatternregime']:
            self.no_s15 = True
        pointer = self.meters.setdefault(serial_no, MeterComparison(mpan=self, serial_no=serial_no))
        pointer = pointer.registers.setdefault(register, RegisterComparison(meter=pointer,
                                                                            register_id=register))
        pointer.add_dynamics_row(row)

    def process_portal_row(self, row):
        serial_no = row['serial_number']
        register = row['register_id']
        serial_no = serial_no.upper() if serial_no else serial_no
        register = register.upper() if register else register
        meter_match_fixed = False
        register_match_fixed = False
        dynamics_meters = [serial_no for serial_no, meter in self.meters.items() if
                           any(register.dynamics_rows for register_id, register in
                               meter.registers.items())]
        for dynamics_serial_no in dynamics_meters:
            if self.check_leading_0s(serial_no, dynamics_serial_no):
                serial_no = dynamics_serial_no
                meter_match_fixed = True
        pointer = self.meters.setdefault(serial_no,
                                         MeterComparison(mpan=self,
                                                         serial_no=serial_no,
                                                         match_fixed=meter_match_fixed))
        dynamics_registers = [register for register, records in pointer.registers.items() if
                              records.dynamics_rows]
        for dynamics_register in dynamics_registers:
            if self.check_leading_0s(register, dynamics_register):
                register = dynamics_register
                register_match_fixed = True
        pointer = pointer.registers.setdefault(register,
                                               RegisterComparison(meter=pointer,
                                                                  register_id=register,
                                                                  match_fixed=register_match_fixed))
        pointer.add_portal_row(row)

    def update_counts(self):
        self.portal_meter_count = len([serial_no for serial_no, meter in self.meters.items() if
                                       any(register.portal_rows for register_id, register in
                                           meter.registers.items())])
        self.dynamics_meter_count = len([serial_no for serial_no, meter in self.meters.items() if
                                         any(register.dynamics_rows for register_id, register in
                                             meter.registers.items())])
        self.meter_match_count = len([serial_no for serial_no, meter in self.meters.items() if any(
            register.dynamics_rows for register_id, register in meter.registers.items()) and any(
            register.portal_rows for register_id, register in meter.registers.items())])
        self.in_portal = True if self.portal_meter_count else False
        self.in_dynamics = True if self.dynamics_meter_count else False
        output_rows = []
        for serial_no, meter in self.meters.items():
            meter.update_counts()
            for register_id, register in meter.registers.items():
                register.update_counts()

    # def determine_meter_action(self):
    #     if self.no_s15:
    #         self.meter_action = 'do nothing'
    #     elif self.portal_meter_count == 1 and self.dynamics_meter_count == 1:
    #         if self.meter_match_count == 1:
    #             self.meter_action = 'do nothing'
    #         elif self.meter_match_count == 0:
    #             self.meter_action = 'overwrite portal meter with serial_no from dynamics register'
    #     elif self.portal_meter_count == self.dynamics_meter_count:
    #         if self.portal_meter_count == self.meter_match_count:
    #             self.meter_action = 'do nothing'
    #         elif self.meter_match_count < self.portal_meter_count:
    #             self.meter_action = 'investigate mismatched meters'
    #     elif self.portal_meter_count < self.dynamics_meter_count:
    #         self.meter_action = 'create missing meters in portal'
    #     elif self.portal_meter_count > self.dynamics_meter_count:
    #         self.meter_action = 'investigate extra meters in portal'
