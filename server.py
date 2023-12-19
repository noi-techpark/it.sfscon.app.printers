import os
import uuid
import time
import json
import httpx
import socket
import signal
import psutil
import dotenv
import signal
import uvicorn
import logging
import pydantic
import subprocess

from telegram import Bot
from fastapi import FastAPI
from telegram.error import TelegramError
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException
# from typing import Optional, Literal

from print import generate
from log import setup_logger

current_file_folder = os.path.dirname(os.path.abspath(__file__))

dotenv.load_dotenv()
log = setup_logger()
app = FastAPI()

_credentials = None
_service_uri = None
_printer_port_forwarding_uri = None
remote_port = None

# class ScanRequest(pydantic.BaseModel):
#     format: Optional[Literal['json', 'png']] = 'png'

def close_tunnel(leave_ssh=True):
    global _printer_port_forwarding_uri
    if _printer_port_forwarding_uri:
        kill_command = '''ps aux | grep ssh  | grep ''' + _printer_port_forwarding_uri + ''' | awk '{print "kill -9 "$2}' | bash'''
        log.debug(kill_command)

        if leave_ssh:
            log.debug("Leaving SSH connection")
            kill_command = '''ps aux | grep ssh  | grep ''' + _printer_port_forwarding_uri + ''' | grep -v ':22 ' | awk '{print "kill -9 "$2}' | bash'''
                
        process = subprocess.Popen(kill_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.communicate()


@app.get('/ping')
async def scan():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
    except:
        uptime_seconds = -1
                
    return {'pong': True, 'uptime_minutes': round(uptime_seconds/60.0,2), 'lane_id': os.getenv('LANE')}

@app.post('/scan/{secret}')
async def scan(secret: str):# , request: ScanRequest):
    global _credentials, _service_uri

    log.info(f"Request received for secret {secret}")
    if not _credentials:
        log.warning(f"Printer not registered yet")
        raise HTTPException(status_code=406, detail='PRINTER_NOT_REGISTERED')

    id_conference = _credentials['id_conference']
    PRETIX_ORGANIZER_ID = _credentials['pretix']['organizer_id']
    PRETIX_EVENT_ID = _credentials['pretix']['event_id']
    PRETIX_CHECKLIST_ID = _credentials['pretix']['checklist_id']
    PRETIX_TOKEN = _credentials['pretix']['token']

    async with httpx.AsyncClient() as client:
        try:
            url = f'https://pretix.eu/api/v1/organizers/{PRETIX_ORGANIZER_ID}/events/{PRETIX_EVENT_ID}/checkinlists/{PRETIX_CHECKLIST_ID}/positions/?secret={secret}'

            log.debug('Creating get request to ' + url)

            res = await client.get(url, headers={'Authorization': f'Token {PRETIX_TOKEN}'})

            log.debug('Response status code is ' + str(res.status_code))

            if res.status_code != 200:
                log.error('Failed to fetch order from pretix: ' + str(res.status_code))
                
                try:
                    printer_x_api_key = os.getenv('PRINTER_X_API_KEY', None)
                    r = await client.post(f'{_service_uri}/api/flows',
                                        json={'conference_id': id_conference,
                                              'pretix_order_id': None,
                                              'text': f'secret not recognized or ticket is not valid secret: {secret}',
                                              'data': res.json()},
                                        headers={'X-Api-Key': printer_x_api_key})
                    
                    log.info(f"R {r}")
                                    
                except:
                    log.error("TICKET_NOT_RECOGNIZED_AT_PRETIX E")
                    ...
                    
                
                raise HTTPException(status_code=403, detail='TICKET_NOT_RECOGNIZED_AT_PRETIX')

            pretix_data = res.json()

            if pretix_data['count'] < 1:
                log.error('Failed to fetch order from pretix (ticket is not recognized): ' + str(res.status_code))

                try:
                    printer_x_api_key = os.getenv('PRINTER_X_API_KEY', None)
                    await client.post(f'{_service_uri}/api/flows',
                                        json={'conference_id': id_conference,
                                              'pretix_order_id': None,
                                              'text': f'secret not recognized or ticket is not valid secret: {secret}',
                                              'data': res.json()},
                                        headers={'X-Api-Key': printer_x_api_key})
                    
                    log.info(f"R2 {r}")
                                    
                except Exception as e:
                    log.error(f"TICKET_NOT_RECOGNIZED_AT_PRETIX E2 {e}")
                    ...

                raise HTTPException(status_code=403, detail='TICKET_NOT_RECOGNIZED_AT_PRETIX')

            first_name = pretix_data['results'][0]['attendee_name_parts']['given_name']
            last_name = pretix_data['results'][0]['attendee_name_parts']['family_name']
            organization = pretix_data['results'][0]['company']

            email = pretix_data['results'][0]['attendee_email']

            log.info(f'Received ticket for {first_name} {last_name} <{email}> ({organization})')

            r = {
                "first_name": first_name,
                "last_name": last_name,
                "organization": organization,
            }

            base_folder = f'{current_file_folder}/printed-labels'
            os.makedirs(base_folder, exist_ok=True)
            image_path = f'{base_folder}/{secret}.png'
            generate(r, image_path)

            log.info(f'Generated ticket in {image_path}')


            if not os.getenv('VIRTUAL_PRINTER',False):

                log.info("Printing image using lpr")
                os.system(f'cp {image_path} /tmp/label.png')
                res = os.system(f'python lpr.py')

                if res != 0:
                    log.warning('Failed do print label after timeout')
                    lane_id = os.getenv('LANE', None)
                    timeout_report_uri = f'{_service_uri}/api/printers/timeout/{lane_id}'
                    try:
                        res = await client.post(timeout_report_uri, headers={'Authorization': f'Token {PRETIX_TOKEN}'})
                    except Exception as e:
                        ...

                    raise HTTPException(status_code=408, detail='PRINTING_TIMEOUTED')

            else:
                log.info("USING VIRTUAL PRINTER - avoid sending image to printer")
                if secret=='d8cpm24fyuv2nn73zasrzgbcynfcfxd3':
                    log.info("SUCCESSFULY PRINT IVO")
                elif secret=='8stuwespjgtaxwecjgkvtfmycbvupq3r.':
                    log.warning("IGOR CAN'T BE PRINTED - Simulating timeout")
                    time.sleep(10)
                    log.warning('Failed do print label after timeout')
                    lane_id = os.getenv('LANE', None)
                    timeout_report_uri = f'{_service_uri}/api/printers/timeout/{lane_id}'
                    try:
                        res = await client.post(timeout_report_uri, headers={'Authorization': f'Token {PRETIX_TOKEN}'})
                    except Exception as e:
                        ...
                        
                    raise HTTPException(status_code=408, detail='PRINTING_TIMEOUTED')
                else: 
                    log.info(f"SUCCESSFULY PRINT {secret}")

            log.info("CHECKING ON PRETIX")
            
            url = f'https://pretix.eu/api/v1/organizers/{PRETIX_ORGANIZER_ID}/checkinrpc/redeem/'
            _body = {'secret': secret,'lists':[PRETIX_CHECKLIST_ID], 'type': 'entry'}
            
            log.info(f"USING {url} {_body}")
            res = await client.post(url,json=_body,headers={'Authorization': f'Token {PRETIX_TOKEN}'})
            
            log.info(f"result status {res.status_code}")
            log.info(f"result text {res.text}")
            
            checkin_response = None
            try:
                checkin_response = res.json()
            except:
                pass

            if res.status_code >=400 and res.status_code < 500:
                error_reason = checkin_response['reason'] if checkin_response and 'reason' in checkin_response else 'unknown reason'
                log.warning(f'Error occured {error_reason}')            
                
            uri = f'{_service_uri}/api/conferences/{id_conference}/scans/lanes/{_credentials["id"]}/{secret}'

            log.debug(f'Registering scan at {uri}')
            try:
                res = await client.post(uri,
                                        json={'pretix_response': pretix_data,
                                              'pretix_checkin_response': checkin_response
                                        },
                                        headers={'Authorization': f'Token {PRETIX_TOKEN}'})

                log.debug(f'Status code {res.status_code}')
                if res.status_code != 200:
                    log.warning(f'Failed to register scan at server: {res.status_code}')
                    raise HTTPException(status_code=403, detail='ERROR_SENDING_INFO_TO_SERVER')
            except Exception as e:
                log.critical("Error registering print on service")

            try:
                bot = Bot(token=_credentials['telegram']['bot_token'])
                chat_ids = _credentials['telegram']['chat_id']

                for chat_id in chat_ids.split(','):
                    with open(image_path, 'rb') as photo:
                        log.debug('Sending generated image to chat_id ' + str(chat_id))
                        await bot.send_photo(chat_id=chat_id, photo=photo)
            except Exception as e:
                log.critical("Error sending info to telegram")
                
            # if request.format == 'png':
            #     log.debug('scan successfully accepted - Returning image as result')
            #     return FileResponse(image_path, media_type='image/png')

            log.debug('scan successfully accepted - Returning json as result')

            p={}
            p['id_location'] = os.getenv('LANE', None)
            p['secret'] = secret
            p['display_name'] = pretix_data['results'][0]['attendee_name']
            p['company'] = pretix_data['results'][0]['company']

            return p

        except Exception as e:
            raise


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}


def fetch_info_from_opencon_uri_finder():
    uri = os.getenv('OPENCON_URI_FINDER')+f'?random={uuid.uuid4()}'

    with httpx.Client() as client:
        res = client.get(uri)

        if res.status_code != 200:
            raise Exception(f'Failed to fetch data from OpenCon URI Finder at {uri}')

        if 'printer_port_forwarding_uri' not in res.json():
            raise Exception(f'Missing printer_port_forwarding_uri in response from OpenCon URI Finder at {uri}')

        return res.json()


def expose_my_local_port(printer_port_forwarding_uri):

    SSH_GATEWAY_PORT = _credentials['external_port']

    LOCAL_APP_PORT = os.getenv('LOCAL_APP_PORT', None)
    if not LOCAL_APP_PORT or str(int(LOCAL_APP_PORT)) != LOCAL_APP_PORT:
        raise Exception('Missing LOCAL_APP_PORT in .env or LOCAL_APP_PORT is not an integer')

    close_tunnel()

    command = f'ssh -R {SSH_GATEWAY_PORT}:localhost:{LOCAL_APP_PORT} {printer_port_forwarding_uri} -N -i ./id_rsa &'
    log.debug(command)
    subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    log.info("Opening ssh tunnel for the remote access")
    SSH_PORT = int(SSH_GATEWAY_PORT)+1000
    command = f'ssh -R {SSH_PORT}:localhost:22 {printer_port_forwarding_uri} -N -i ./id_rsa &'

    log.debug(command)
    subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return int(LOCAL_APP_PORT), int(SSH_GATEWAY_PORT)


def is_uuid(x):
    try:
        uuid.UUID(x)
        return True
    except:
        return False


def register_printer(service_uri):
    with httpx.Client() as client:

        lane_id = os.getenv('LANE', None)
        if not lane_id or not is_uuid(lane_id):
            raise Exception('Missing LANE in .env or LANE is not a valid UUID')

        printer_x_api_key = os.getenv('PRINTER_X_API_KEY', None)
        if not printer_x_api_key or not is_uuid(printer_x_api_key):
            raise Exception('Missing PRINTER_X_API_KEY in .env or PRINTER_X_API_KEY is not a valid format')

        try:
            global remote_port
            uri = service_uri + f'/api/printers/register/{lane_id}'
            res = client.post(service_uri + f'/api/printers/register/{lane_id}',
                              json={'test_endpoint': f"http://{_printer_port_forwarding_uri.split('@')[-1]}:[remote_port]/scan/d8cpm24fyuv2nn73zasrzgbcynfcfxd3"},
                              headers={'X-Api-Key': printer_x_api_key})

#            print("SENDING ",{'test_endpoint': f"http://{_printer_port_forwarding_uri.split('@')[-1]}:{remote_port}/scan/d8cpm24fyuv2nn73zasrzgbcynfcfxd3"})

            if res.status_code != 200:
                raise Exception(f'Failed to register printer at {service_uri}')

            credentials = res.json()

            with open('credentials.json', 'wt') as f:
                json.dump(credentials, f, indent=4)
        except Exception as e:

            log.critical("Can not access server or error registering printer, using cached version if exists")

            try:
                with open('credentials.json', 'rt') as f:
                    credentials = json.load(f)
            except Exception as e:
                raise Exception(f'Failed to register printer at {service_uri}')

        return credentials


#def close_tunnel():
#
#    global _printer_port_forwarding_uri
#
#    log.info("Closing Tunnel")
#    if _printer_port_forwarding_uri:
#        kill_command = '''ps aux | grep ssh  | grep ''' + _printer_port_forwarding_uri + ''' | awk '{print "kill -9 "$2}' | bash'''
#        log.debug(kill_command)
#        process = subprocess.Popen(kill_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#        process.communicate()

@app.on_event("shutdown")
async def shutdown_event():

    with httpx.Client() as client:
        
        lane_id = os.getenv('LANE', None)
        printer_x_api_key = os.getenv('PRINTER_X_API_KEY', None)

        res = client.post(_service_uri + f'/api/printers/unregister/{lane_id}',
                          headers={'X-Api-Key': printer_x_api_key})

    log.critical('CTRL+C Pressed')
    close_tunnel(True)

def kill_all_python_scripts_except_myself():
    current_process = psutil.Process(os.getpid())

    for proc in psutil.process_iter(['pid', 'name']):
        if 'python' in proc.info['name'].lower():
            if proc.pid != current_process.pid:
                os.kill(proc.pid, signal.SIGTERM)
                time.sleep(2)
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                except Exception as e:
                    pass
                                

if __name__ == "__main__":

    kill_all_python_scripts_except_myself()
    
    uri_finder_json = fetch_info_from_opencon_uri_finder()
    printer_port_forwarding_uri = uri_finder_json['printer_port_forwarding_uri']
    _printer_port_forwarding_uri = printer_port_forwarding_uri
    _service_uri = uri_finder_json['service_uri']

    _credentials = register_printer(_service_uri)

    app_port, remote_port = expose_my_local_port(printer_port_forwarding_uri)

    log.info(f"Successfully registered on server {_service_uri} and got pretix credentials")
    # print(f"Successfully registered on server {_service_uri} and got pretix credentials")
    log.info(json.dumps(_credentials, indent=4))
    # print(json.dumps(_credentials, indent=4))

    log.info("Running server locally on " + str(printer_port_forwarding_uri))
    log.info('\n')
    log.info(f"Test Printer using: \ncurl -X POST http://{printer_port_forwarding_uri.split('@')[-1]}:{remote_port}/scan/d8cpm24fyuv2nn73zasrzgbcynfcfxd3")
    log.info('\n')
    # print("Running server locally on " + str(app_port))

    log.info("Visible from the outside on " + str(printer_port_forwarding_uri).split('@')[1] + ":" + str(remote_port))
    # print("Visible from the outside on " + str(printer_port_forwarding_uri).split('@')[1] + ":" + str(remote_port))

    uvicorn.run(app, host="0.0.0.0", port=app_port)
