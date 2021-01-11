

import json
import aiohttp
import asyncio

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.http import AsyncHttpConsumer
from channels.db import database_sync_to_async
from asyncio.queues import Queue, QueueEmpty, QueueFull
from django.core.exceptions import ObjectDoesNotExist


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
        print(data)
        data['data'] = 42
        
        url, rsp = await self.build_request(data)

        if len(url) == 0:
            await self.send(json.dumps(rsp))

        await self.send(json.dumps(data))


    ########################
    #   relay_request
    #   sends a request to an external
    #   device url
    #   Returns the response or timeout error
    ########################
    # async def ext_http_post(self, url, data):

    #     result = 0
    #     response_data = {}

    #     async with aiohttp.ClientSession(timeout=API_EXT_HTTP_RQ_TIMEOUT) as s:
    #         async with s.post(url, json=data) as rsp:
    #             if len(rsp.json) > API_MAX_HTTP_DATA_LEN:
    #                 print("Error: Excess data")
    #                 response_data['error_code'] = ERR_CODE_INVALID_RESPONSE_LEN
    #                 response_data['message'] = "Excess response data"
    #             else:
    #                 result = rsp.status
    #                 try:
    #                     response_data = await rsp.json()
    #                     print(response_data)
    #                 except:
    #                     print("Error unpacking JSON")
    #                     response_data['error_code'] = ERR_CODE_INVALID_JSON
    #                     response_data['message'] = "Invalid json"

    #     return result, response_data


    # async def ext_websocket(self):
    #     pass



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


            url = device_object.ip_address
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

