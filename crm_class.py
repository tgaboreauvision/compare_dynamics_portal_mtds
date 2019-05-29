import csv
from inspect import getmembers
from pprint import pprint
import settings
import requests
import uuid
import time


class Odata():

    def __init__(self, sandbox, odata_username, odata_password):
        if sandbox:
            sandbox_flag = 'sandbox'
        else:
            sandbox_flag = ''
        self.crmorg = f'https://togetherenergy{sandbox_flag}.crm11.dynamics.com'  # base url for crm org
        self.clientid = 'd3be38a1-f508-401c-aa24-57db6af0b083'  # application client id
        self.username = odata_username  # username
        self.userpassword = odata_password  # password
        self.tokenendpoint = 'https://login.microsoftonline.com/00b00e7f-ac76-4fd6-95a4-1e59637ce7a0/oauth2/token'  # oauth token endpoint
        self.crmwebapi = f'https://togetherenergy{sandbox_flag}.crm11.dynamics.com/api/data/v9.0'  # full path to web api endpoint
        self.accesstoken = None
        self.crmrequestheaders = {
            'Authorization': None,
            'OData-MaxVersion': '4.0',
            'OData-Version': '4.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=utf-8',
            'Prefer': 'return=representation'
        }

    def get_access_token(self):
        # build the authorization token request
        tokenpost = {
            'client_id': self.clientid,
            'resource': self.crmorg,
            'username': self.username,
            'password': self.userpassword,
            'grant_type': 'password'
        }
        tokenres = requests.post(self.tokenendpoint, data=tokenpost)
        try:
            self.accesstoken = tokenres.json()['access_token']
            self.crmrequestheaders['Authorization'] = 'Bearer ' + self.accesstoken
        except KeyError as e:
            print('Cannot get access token.')

    def get_req(self, entity, top = None, select = None, fltr = None, textquery=None, printprogress = True):
        if textquery:
            crmwebapiquery = textquery
        else:
            top_param = ''
            select_param = ''
            filter_param = ''
            if top:
                top_param = '$top={0}'.format(top)
            if select:
                select_param = '$select={0} '.format(','.join(select))
            if fltr:
                filter_param = '$filter={0}'.format(fltr)
            params = (top_param, select_param, filter_param)
            param_string = '&'.join([p for p in params if p])
            crmwebapiquery = '/{0}?{1}'.format(entity, param_string)
        # print(crmwebapiquery)
        # try:
        results = self.get_all_data(crmwebapiquery, printprogress)
        # except (ValueError, requests.exceptions.ConnectionError):
        #     self.get_access_token()
        #     if attempt < 5:
        #         time.sleep(5)
        #         attempt += 1
        #         print('oData failure. retrying - attempt {0}'.format(attempt))
        #         results = self.get_req(entity, top, select, fltr, attempt)
        #     else:
        #         return None
        return results

    def get_page(self, url, attempt=1):
        try:
            crmres = requests.get(url, headers=self.crmrequestheaders)
            # pprint(getmembers(crmres))
            crmresults = crmres.json()
            records = crmresults['value']
            next_link = crmresults['@odata.nextLink'] if '@odata.nextLink' in crmresults else None
        except (ValueError, requests.exceptions.ConnectionError):
            self.get_access_token()
            if attempt < 5:
                time.sleep(5)
                attempt += 1
                print('oData failure. retrying - attempt {0}'.format(attempt))
                records, next_link = self.get_page(url, attempt=attempt)
            else:
                return None
        return records, next_link

    def get_all_data(self, api_query, printprogress):
        url = self.crmwebapi + api_query
        records = []
        next_link = url
        while next_link:
            if records and printprogress:
                print(len(records))

            query_results = self.get_page(next_link)
            # for el in query_results:
            #     print(type(el))
            new_records, next_link = query_results[0], query_results[1]
            records = records + new_records
        return records

    def post_req(self, entity, data):
        crmwebapiquery = '/{0}'.format(entity)
        url = self.crmwebapi + crmwebapiquery
        # print crmwebapiquery
        # pprint(data)
        result = requests.post(
            url,
            headers=self.crmrequestheaders,
            data=str(data)
        )
        return result

    def patch_req(self, entity, record_id, data):
        crmwebapiquery = '/{0}({1})'.format(entity, record_id)
        url = self.crmwebapi + crmwebapiquery
        # print crmwebapiquery
        # pprint(data)
        result = requests.patch(
            url,
            headers=self.crmrequestheaders,
            data=str(data)
        )
        return result

    def del_req(self, entity, record_id):
        crmwebapiquery = '/{0}({1})'.format(entity, record_id)
        url = self.crmwebapi + crmwebapiquery
        response = requests.delete(
            url,
            headers=self.crmrequestheaders
        )
        return response

    def get_supply_points(self, mpan):
        try:
            supply_points = self.get_req(
                'd4e_energy_supply_points',
                fltr="d4e_mpxn eq '{0}'".format(mpan)
            )
        except IndexError:
            return None
        return supply_points

    def get_meters(self, mpan_id):
        try:
            meters = self.get_req(
                'd4e_meters',
                fltr="_d4e_esp_meter_value eq '{0}'".format(mpan_id)
            )
        except KeyError:
            return None
        return meters

    def get_meter(self, serial_number, mpan_id):
        try:
            meters = self.get_req(
                'd4e_meters',
                fltr="d4e_serial_number eq '{0}' and _d4e_esp_meter_value eq '{1}'".format(serial_number, mpan_id)
            )
        except KeyError as e:
            return None
        return meters

    def get_register(self, register_id, meter_id):
        registers = self.get_req(
            'd4e_registers',
            fltr="d4e_meterregisterid eq '{0}' and _d4e_meterregisters_value eq '{1}'".format(register_id, meter_id)
        )
        return registers

    def write_log(self, mpxn, message, direction, message_type, processing_status, created_by, filename):
        data = {
            'd4e_cfa_msg_iid': '{0}'.format(uuid.uuid4()),
            'd4e_cfa_parent_loopid': '{0}'.format(mpxn),
            'd4e_message_text': message,
            'd4e_direction': direction,
            'd4e_message_type': message_type,
            'd4e_processing_status': processing_status,
            'd4e_mpxn': '{0}'.format(mpxn),
            'd4e_log_created_by': created_by,
            'd4e_message_filename' : filename

        }
        self.post_req('d4e_in_tx_cfa_msg_tests', data)


    def squash(self, value):
        if isinstance(value, str):
            return ''.join([char if ord(char) < 128 else '?' for char in value])
        else:
            return value

    def write_csv(self, filename, data, fieldnames = None):
        if not fieldnames:
            fieldnames = []
        with open(filename, 'w', newline='') as csvfile:
            for record in data:
                for k in record:
                    if k not in fieldnames:
                        fieldnames.append(k)
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                row = {self.squash(k): self.squash(v) for k, v in row.items()}
                writer.writerow(row)

