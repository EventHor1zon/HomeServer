

import json
import aiohttp
import asyncio

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.http import AsyncHttpConsumer
from channels.db import database_sync_to_async
from asyncio.queues import Queue, QueueEmpty, QueueFull
from django.core.exceptions import ObjectDoesNotExist

from datetime import datetime

from .command_api import *
from . import models



API_EXT_HTTP_RQ_TIMEOUT = 10
API_MAX_HTTP_DATA_LEN = 1024




async def process_task(self, request):
# TODO: Maybe make this able to do more than one op?
    url, data = self.build_request(request)
    
    if not len(url):
        # send an error response
        self.dispatch(data)
    else:
        result, response = await self.ext_http_post(url, data)
        # TODO: update models here then dispatch back to page
        # self.update_models_from_response() if response['rsp_type'] != RSP_TYPE_ERR
        self.dispatch(response)



class DataConsumer(AsyncWebsocketConsumer):

    def __init__(self, **kwargs):
        super().__init__()
        self.input_queue = Queue(100)
        

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        url, rq = await self.build_request(data)
        if len(url) == 0:
            await self.send(json.dumps(rq))
        else:
            result, response = await self.ext_http_post(url, rq)
            await self.send(json.dumps(response))
            await self.update_peripheral(response)

    ########################
    #   relay_request
    #   sends a request to an external
    #   device url
    #   Returns the response or timeout error
    ########################
    async def ext_http_post(self, url, data):

        result = True
        response_data = {}
        print("Posting")

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json=data) as rsp:
                    result = rsp.status
                    print(rsp)
                    try:
                        response_data = await rsp.json()
                        print(response_data)
                    except:
                        print("Error unpacking JSON")
                        response_data['error_code'] = ERR_CODE_INVALID_JSON
                        response_data['message'] = "Invalid json"
        except aiohttp.ClientTimeout:
            print("TimeoutError")
            response_data = {"rsp_type": RSP_TYPE_ERR, "message": "Timeout in device!", "code": 500}
            result = False
        return result, response_data


    ########################
    #   build_request(data)
    #   parses incomming json request
    #   returns json string  
    #   to relay & target or error response
    ########################
    async def build_request(self, data):
        print("Building request")
        device_object = None
        param_object = None
        url = ""
        ret = ()
        request = {}
        error_rsp = { 'rsp_type': RSP_TYPE_ERR, 'error_code':0 }
    
        fail = False

        if not check_basic_keys(data):
            error_rsp['message'] = "Missing Json fields!"
            error_rsp['error_code'] = ERR_CODE_MISSING_FIELD
            fail = True

        if not fail:

            fail = await self.is_invalid_dev(int(data['dev_id']))
            if fail:
                error_rsp['message'] = "Invalid device id"
                error_rsp['error_code'] = ERR_CODE_INVALID_DEV_ID
            else:
                fail = await self.is_invalid_periph(int(data['dev_id']), int(data['periph_id']))
                if fail:
                    error_rsp['message'] = "Invalid periph id"
                    error_rsp['error_code'] = ERR_CODE_INVALID_PERIPH_ID
                else:
                    fail = await self.is_invalid_param(int(data['periph_id']), int(data['param_id']))
                    if fail:
                        error_rsp['message'] = "Invalid param id"
                        error_rsp['error_code'] = ERR_CODE_INVALID_PARAM_ID

        if not fail:

            cmd_type = CommandTypeToInteger(data['cmd_type'])
            dev_id = int(data['dev_id'])
            periph_id = int(data['periph_id'])
            param_id = int(data['param_id'])
            data = int(data['data'])
            param_object = await self.get_param_object(dev_id, periph_id, param_id)
            if param_object == None:
                print("Failed in param database lookup!")
                error_rsp['message'] = "Invalid ID for command"
                error_rsp['error_code'] = ERR_CODE_INVALID_CMD_PARAMS
                fail = True

            device_object = await self.get_device_object(dev_id)

            if device_object == None:
                print("Failed in device database lookup!")
                error_rsp['message'] = "Invalid ID for command"
                error_rsp['error_code'] = ERR_CODE_INVALID_CMD_PARAMS
                fail = True
        
        if not fail:

            if cmd_type != CMD_TYPE_INFO and (dev_id == 0 or periph_id == 0 or param_id == 0): 
                error_rsp['message'] = "Invalid ID for command"
                error_rsp['error_code'] = ERR_CODE_INVALID_CMD_PARAMS
                fail = True
            elif cmd_type == CMD_TYPE_SET and not check_set_keys(request):
                error_rsp['message'] = "Missing keys"
                error_rsp['error_code'] = ERR_CODE_MISSING_FIELD
                fail = True
            elif cmd_type == CMD_TYPE_SET and data > param_object.max_valid:
                error_rsp['message'] = "Value greater than max!"
                error_rsp['error_code'] = ERR_CODE_INVALID_CMD_PARAMS
                fail = True
            

        if not fail:
            ## build the request
            request['cmd_type'] = cmd_type
            request['periph_id'] = periph_id
            request['param_id'] = param_id

            if cmd_type == CMD_TYPE_SET:
                request['data_type'] = param_object.data_type
                request['data'] = data

            else:
                request['data'] = 0
                request['data_type'] = 0       

            url = "http://"
            url += device_object.ip_address
            url += ":"
            url += str(device_object.api_port)
            if not device_object.cmd_url.startswith("/"):
                url += "/"
            url += device_object.cmd_url


        # found an error in the json request
        if fail:
            ret = ("", error_rsp)
        else:
        # return the url & request data
            ret = (url, request)

        print(ret)
        return ret



    @database_sync_to_async
    def get_param_object(self, dev_id, periph_id, param_id):
        try:
            param = models.Parameter.objects.filter(peripheral__id=periph_id).filter(peripheral__device__id=dev_id).get(id=periph_id)
            return param
        except ObjectDoesNotExist:
            print("Invalid id")
            return None

    @database_sync_to_async
    def get_device_object(self, dev_id):
        try:
            dev = models.Device.objects.get(id=dev_id)
            return dev
        except ObjectDoesNotExist:
            print("Invalid id")
            return None

    @database_sync_to_async
    def is_invalid_dev(self, dev_id):
        if dev_id == 0:
            return False
        else:
            try:
                obj = models.Device.objects.get(id=dev_id)
                return False
            except ObjectDoesNotExist:
                return True

    @database_sync_to_async
    def is_invalid_periph(self, dev_id, p_id):
        if p_id == 0:
            return False
        else:
            try:
                obj = models.Peripheral.objects.filter(device__id=dev_id).get(id=p_id)
                return False
            except ObjectDoesNotExist:
                return True
            
    @database_sync_to_async
    def is_invalid_param(self, p_id, prm_id):
        if prm_id == 0:
            return False
        else:
            try:
                obj = models.Parameter.objects.filter(peripheral__id=p_id).get(id=prm_id)
                return False
            except ObjectDoesNotExist:
                return True




###
#   Discoverer  - the websocket class for the discover & enumerate functionality

class Discoverer(AsyncWebsocketConsumer):

    ## Websocket receive ##
    async def receive(self, text_data):
        
        data = json.loads(text_data)
        target = data['ip_addr']
        ext = data['extension']
        port = data['port']

        await self.send(json.dumps({"data": f"> Enumerating device at [{target}]", "code": 1}))

        await self.enumerate_device(target, port, ext)


    ## Enumerate the device at target:port/extension
    async def enumerate_device(self, target, port, extension):

        data = {"cmd_type": 0,
                "periph_id": 0,
                "param_id": 0,
                "data": 0,
                "data_type": 0
                }

        dev_name = ""
        periph_ids = []
        periph_num = 0
        device_id = 0
        peripherals = []
        
        url = "http://"
        url += target
        url += ":"
        url += str(port)
        if(extension[0] != "/"):
            url+="/"
        url += extension
        fail = False

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json=data) as rsp:
                    status = rsp.status
                    await self.send(json.dumps({"data": "> Got response [" + str(status) + "]", "code": status}))
                    data = await rsp.json()
                    dev_name = data['name']
                    periph_ids = data['periph_ids']
                    periph_num = data['periph_num']
                    device_id = data['dev_id']

                    if(type(periph_ids) != list):
                        await self.send(json.dumps({"data": "> Got weird list! FAILED"}))
                        fail = True

        except aiohttp.ClientConnectionError:
            await self.send(json.dumps({"data": "Error: Device is unnreachable!", "code": 504}))
            fail = True
        except aiohttp.InvalidURL:
            await self.send(json.dumps({"data": "Error: Invalid URL!"}))
            fail = True

        ## check device is not already enumerated...
        if not fail:
            if self.is_existing_device(device_id):
                await self.send(json.dumps({"data": "Error: Device already exists! Try /update", "code": 508}))
                fail = True
               

        ## sanity checking the json type
        if not fail:
            p_info = {
                "cmd_type": 0,
                "periph_id": 0,
                "param_id": 0,
                "data": 0,
                "data_type": 0
            }

            for p in periph_ids:
                p_info['periph_id'] = p
                p_model = {
                    "param_ids": [],
                    "name": 0,
                    "param_num": 0,
                    "periph_id": 0,
                    'sleep_state': 0,
                    'is_powered': True,
                    "params": [],
                }

                try:
                    async with aiohttp.ClientSession() as s:
                        async with s.post(url, json=p_info) as rsp:
                            p_data = await rsp.json()
                            p_model["param_ids"] = p_data['param_ids']
                            p_model["name"] = p_data['name']
                            p_model["param_num"] = p_data['param_num']
                            p_model["periph_id"] = p_data['periph_id']    
                except aiohttp.ClientResponseError:
                    await self.send(json.dumps({"data": "Bad response from device! FAIL", "code": 505}))
                    fail = True
                except KeyError:
                    await self.send(json.dumps({"data": "Missing keys in response!", "code": 505}))


                if not fail:
                    await self.send(json.dumps({"data": f"Enumerated: Peripheral {p_model['name']} [{p_model['periph_id']}]- {p_model['param_num']} Parameters", "code": 201}))

                    prm_info = {
                        "cmd_type": 0,
                        "periph_id": p,
                        "param_id": 0,
                        "data": 0,
                        "data_type": 0,
                        "is_gettable": False,
                        "is_settable": False,
                        "is_action": False,            
                    }

                    for param in p_model['param_ids']:
                        print("sending")
                        print(param)
                        prm_info['param_id'] = param
                        try:
                            prm_model = {
                                'name': "",
                                'periph_id': 0,
                                'param_id': 0,
                                'param_type': 0,
                                'methods': 0,
                                'max_value': 0,
                                'data_type': 0,
                            }
                            async with aiohttp.ClientSession() as s:
                                async with s.post(url, json=prm_info) as rsp:
                                    prm_data = await rsp.json()  
                                    prm_model['name'] = prm_data['param_name']
                                    prm_model['periph_id'] = prm_data['periph_id']
                                    prm_model['param_id'] = prm_data['param_id']
                                    prm_model['param_type'] = prm_data['param_type']
                                    prm_model['methods'] = prm_data['methods']
                                    prm_model['max_value'] = prm_data['param_max']
                                    prm_model['data_type'] = prm_data['data_type']

                                    p_model['params'].append(prm_model)
                        except aiohttp.ClientResponseError:
                            await self.send(json.dumps({"data": "Bad response from device! FAIL", "code": 505}))
                            fail = True
                        except KeyError:
                            await self.send(json.dumps({"data": "Missing keys in response!", "code": 505}))
                            fail = True

                        if not fail:
                            await self.send(json.dumps({"data": f"Enumerated: [child {p_model['periph_id']}]Parameter: {prm_model['name']} [{prm_model['param_id']}]", "code": 201}))

                peripherals.append(p_model)

        if not fail:
            await self.send(json.dumps({"data": " Device succesfully enumerated", "code": 200 }))
            await self.send(json.dumps({"data": " Engaging database... standby", "code": 200 }))
        else:
            await self.send(json.dumps({"data": "Device enumeration failed :(", "code": 506 }))
        

        if not fail:
            ## log items to the database

            device_info = { 
                            "name": dev_name,
                            "periph_num": periph_num,
                            "dev_id": device_id,
                            "last_polled": datetime.now(),
                            "ip_addr": target,
                            "api_port": int(port),
                            "cmd_url": extension,
                            "num_peripherals": periph_num, 
                            "sleep_state": 0,
                            "is_powered": True,
                            "setup_date": datetime.now(),
                            }

            result = await self.build_new_device(device_info)
            
            if not result:
                await self.send(json.dumps({"data": "- failed when creating new device", "code": 506 }))
                fail = True
            else:
                await self.send(json.dumps({"data": "- Created new Device [id]", "code": 201}))

            if not fail:
                for item in peripherals:
                    item['device'] = device_info['dev_id']
                    
                    result = await self.build_new_peripheral(item)

                    if not result:
                        await self.send(json.dumps({"data": "- - failed when creating new peripheral", "code": 506}))
                        fail = True
                    else:
                        await self.send(json.dumps({"data": "- - Created new Peripheral [id]", "code": 201}))

                    if not fail: 
                        for p in item['params']:

                            p['is_gettable'] = ((p['methods'] & API_GET_MASK) > 0)
                            p['is_settable'] = ((p['methods'] & API_SET_MASK) > 0)
                            p['is_action'] = ((p['methods'] & API_ACT_MASK) > 0)

                            result = await self.build_new_parameter(p)

                            if not result:
                                await self.send(json.dumps({"data": "- - - failed when creating new parameter", "code": 506}))
                                fail = True
                            else:
                                await self.send(json.dumps({"data": "- - - Created new Parameter [id]", "code": 201}))

            if not fail:
                await self.send(json.dumps({"data": "Succesfully enumerated Device!", "code": 201}))
            else:
                await self.send(json.dumps({"data": "Failed to Enumerate Device :(", "code": 506 }))
   


    @database_sync_to_async
    def is_existing_device(self, d_id):
        exists = True
        try:
            D = models.Device.objects.get(device_id=d_id)
        except ObjectDoesNotExist:
            exists = False
        return exists


    @database_sync_to_async
    def build_new_device(self, d_info):
        success = True
        try:
            D = models.Device(
                name=d_info['name'],
                dev_id=d_info['dev_id'],
                last_polled=d_info['last_polled'],
                ip_address=d_info['ip_addr'],
                api_port=d_info['api_port'],
                cmd_url=d_info['cmd_url'],
                num_peripherals=d_info['num_peripherals'],
                sleep_state=d_info['sleep_state'],
                is_powered=d_info['is_powered'],
                setup_date=d_info['setup_date'],
            )
        except KeyError:
            print("Key Error!")
            raise
            success = False
        except:
            raise

        if success:
            try:
                D.save()
            except:
                success = False
        return success

    @database_sync_to_async
    def build_new_peripheral(self, p_info):
        success = True

        try:
            D = models.Device.objects.get(dev_id=p_info['device'])

            P = models.Peripheral(
                periph_id=p_info['periph_id'],
                device=D,
                name=p_info['name'],
                num_params=p_info['param_num'],
                sleep_state=p_info['sleep_state'],
                is_powered=p_info['is_powered'],
            )

        except KeyError:
            print("Key Error!")
            success = False
            raise
        except ObjectDoesNotExist:
            print("Parent Object does not exist!")
            success = False


        if success:
            try:
                P.save()
            except:
                success = False
                raise
        return success


    @database_sync_to_async
    def build_new_parameter(self, prm_info):
        success = True

        try:
            Per = models.Peripheral.objects.get(periph_id=prm_info['periph_id'])

            P = models.Parameter(
                param_id=prm_info['param_id'],
                peripheral=Per,
                name=prm_info['name'],
                max_value=prm_info['max_value'],
                data_type=prm_info['data_type'],
                is_getable=prm_info['is_gettable'],
                is_setable=prm_info['is_settable'],
                is_action=prm_info['is_action'],
            )

        except KeyError:
            print("Key Error!")
            success = False
            raise
        except ObjectDoesNotExist:
            print("Parent Object does not exist!")
            success = False
        except:
            raise

        if success:
            try:
                P.save()
            except:
                success = False
                raise
        return success











