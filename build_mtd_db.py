from to_postgres import db_builder
import settings

# create instance of builder class
new_db = db_builder(settings.postgres_target_db, settings.postgres_target_password)

# create target db
new_db.create_target_db(drop_existing=False)

#  add postgres source
new_db.add_source_conn('portal',
                       'postgres',
                       host=settings.portal_host,
                       user=settings.portal_user,
                       password=settings.portal_password,
                       dbname=settings.portal_db)


#  add portal tables
new_db.add_table('portal_elec_mtds',
                 'sql',
                 'portal',
                 query=open('portal_elec_query.txt', 'r').read())

new_db.add_table('portal_gas_mtds',
                 'sql',
                 'portal',
                 query=open('portal_gas_query.txt', 'r').read())

new_db.add_table('portal_tprs',
                 'sql',
                 'portal',
                 query='select * from meter_mpantimepatternregime')


#  add dynamics_tables
new_db.add_table('supply_points',
                 source='odata',
                 entity='d4e_energy_supply_points')

new_db.add_table('meters',
                 source='odata',
                 entity='d4e_meters')

new_db.add_table('registers',
                 source='odata',
                 entity='d4e_registers')


# add views - N.B. this might throw an error if views already exist, didn't manage to handle
#  these exceptions in the limited time i had
new_db.add_view('dynamics_elec_mtds', open('dynamics_elec_mtds.txt', 'r').read())
new_db.add_view('dynamics_gas_mtds', open('dynamics_gas_mtds.txt', 'r').read())

