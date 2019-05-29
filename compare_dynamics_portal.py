import csv
import os
from pprint import pprint
import pandas as pd
import settings
from sqlalchemy import create_engine
from compare_mtds import MpanComparison

#  engine string to access postgres instance
#  this will only work for a local postgres instance will need to update 'localhost' in string
#  to change this
engine_string = f'postgresql://postgres:{settings.postgres_target_password}@localhost:5432/{settings.postgres_target_db}'

engine = create_engine(engine_string)


#  builds lists of dictionaries of MTDs from local database
#  one list for dynamics elec, one list or portal elec
#  each row = one register
dynamics_df = pd.read_sql_query('select * from dynamics_elec_mtds', con=engine)
dynamics = dynamics_df.to_dict(orient='records')
portal_df = pd.read_sql_query('select * from portal_elec_mtds', con=engine)
portal = portal_df.to_dict(orient='records')


#  iterates through all MTDs, starting with all dynamics and creates/updates an instance of
#  the MpanComparison
comparison_mpans = {}
for row in dynamics:
    mpan = row['d4e_mpxn']
    comparison_mpan = comparison_mpans.setdefault(mpan, MpanComparison(mpan))
    comparison_mpan.process_dynamics_row(row)


#  it is important to process all dynamics rows before processing portal rows...because the
#  logic in the class mpan.process_portal_row() function depends on this
for row in portal:
    mpan = row['meter_point_number']
    comparison_mpan = comparison_mpans.setdefault(mpan, MpanComparison(mpan))
    comparison_mpan.process_portal_row(row)


#  creates the empty lists which will be used to generate the output files
comparison = []
create = []
update_tpr = []
update_leading_0 = []
duplicate_portal_registers = []


#  iterate through each instance of the MpanComparison class and perform the comparison functions
#  output the necessary rows from the functions
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

#  csv writer with error handling
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
        action = input("""Target file is open, what should i do?
        type 'skip' to skip writing this file
        type 'rename' to prefix the filename with copy_
        type 'retry' if you have closed the file: """)
        if action.lower() == 'skip':
            print(f'Skipping file: {filename}')
            return None
        elif action.lower() == 'rename':
            write_csv(f'copy_{filename}', data, fieldnames=fieldnames)
        elif action == 'retry':
            write_csv(filename, data, fieldnames=fieldnames)


#  write csvs
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
