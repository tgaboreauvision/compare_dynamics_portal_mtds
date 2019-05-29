import csv
import os
from pprint import pprint
import pandas as pd
import settings
from sqlalchemy import create_engine
from compare_mtds import MpanComparison, MeterComparison, RegisterComparison

engine_string = f'postgresql://postgres:{settings.postgres_target_password}@localhost:5432/{settings.postgres_target_db}'

engine = create_engine(engine_string)

dynamics_df = pd.read_sql_query('select * from dynamics_elec_mtds', con=engine)
dynamics = dynamics_df.to_dict(orient='records')
portal_df = pd.read_sql_query('select * from portal_elec_mtds', con=engine)
portal = portal_df.to_dict(orient='records')

comparison_mpans = {}

for row in dynamics:
    mpan = row['d4e_mpxn']
    comparison_mpan = comparison_mpans.setdefault(mpan, MpanComparison(mpan))
    comparison_mpan.process_dynamics_row(row)

for row in portal:
    mpan = row['meter_point_number']
    comparison_mpan = comparison_mpans.setdefault(mpan, MpanComparison(mpan))
    comparison_mpan.process_portal_row(row)

comparison = []
create = []
update_tpr = []
update_leading_0 = []
duplicate_portal_registers = []

counter = 0
for mpan, comparison_mpan in comparison_mpans.items():
    counter += 1
    if not counter%1000:
        print(counter)
    comparison_mpan.update_counts()
    if comparison_mpan.no_s15:
        continue
    for serial_no, meter in comparison_mpan.meters.items():
        for register_id, register in meter.registers.items():
            register_output = register.output_comparison_rows()
            comparison = comparison + register_output['comparison']
            create = create + register_output['create']
            update_tpr = update_tpr + register_output['update_tpr']
            update_leading_0 = update_leading_0 + register_output['update_leading_0']
            duplicate_portal_registers = duplicate_portal_registers + register_output['duplicate_portal_registers']


def write_csv(filename, data, fieldnames=None):
    if not fieldnames:
        fieldnames = []
        for row in data:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    except IOError:
        action = input('Target file is open, what should i do?: ')
        if action.lower() == 'skip':
            print(f'Skipping file: {filename}')
            return None
        elif action.lower() == 'rename':
            write_csv(f'copy_{filename}', data, fieldnames=fieldnames)
        elif action == 'retry':
            write_csv(filename, data, fieldnames=fieldnames)



write_csv(os.path.join(settings.output_path, 'full_comparison.csv'),
          comparison)
write_csv(os.path.join(settings.output_path, 'create_portal_registers.csv'),
          create)
write_csv(os.path.join(settings.output_path, 'update_tprs.csv'),
          update_tpr)
write_csv(os.path.join(settings.output_path, 'update_leading_zero.csv'),
          update_leading_0)
write_csv(os.path.join(settings.output_path, 'duplicate_portal_registers.csv'),
          duplicate_portal_registers)
