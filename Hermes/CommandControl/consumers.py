

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

DEBUG = 1

API_EXT_HTTP_RQ_TIMEOUT = 10
API_MAX_HTTP_DATA_LEN = 1024

API_WEBSOCKET_INCOMMING_STREAM_EXTENSION = "/stream"





def error_response(err_code: int, msg=None):

    if err_code not in error_messages.keys():
        err_code = 0
        msg = "unknown error!"
    elif msg == None:
        msg = error_messages[err_code]
    
    error_response = { 
         "rsp_type": RSP_TYPE_ERR,
         "err_code": err_code,
         "msg": msg
     }

    return error_response




def check_json_errors(data: dict, keys: list):
    """ utility function to check presence of keys 
        and their types
    """
    missing_keys = []
    bad_types = []

    for keystring, keytype in keys:
        if keystring not in data.keys():
            missing_keys.append(keystring)
        elif data[keystring].type() != keytype:
            bad_types.append(keystring)
    
    return missing_keys, bad_types


########################
#   relay_request
#   @brief sends a request to an external
#   @param device url
#   @return status & dictionary of results
########################
async def ext_http_post(url: str, data: dict):

    result = 0
    response_data = {}
    debug_print(f"posting data to {url}")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=data) as rsp:
                response_data = await rsp.json()
                debug_print("sent")
                debug_print(data)
                debug_print(f"Got response: (status: {rsp.status})")
                debug_print(response_data)
                result = HTTP_RSP_AQUIRED
    except json.JSONDecodeError:
        result = ERR_CODE_INVALID_RSP_JSON
    except aiohttp.ClientTimeout:
        result = ERR_CODE_HTTP_TIMEOUT
    except aiohttp.InvalidURL:
        result = ERR_CODE_INVALID_URL

    return result, response_data


##
#   @brief updates a parameter model value
#   @data  dictionary data from a set request
#   @param_object parameter model
###
@database_sync_to_async
def update_parameter(data, param_object):
    if type(data) == str and param_object.data_type != PARAMTYPE_STRING:
        try:
            d = int(data)
        except ValueError:
            try:
                d = float(data)
            except:
                print("Error in converting value type: " + type(d))
    else:
        d = data
    try:
        if param_object != None and param_object.last_value != d:
            if param_object.data_type == PARAMTYPE_STRING:
                param_object.last_value_string = str(d)
            else:
                param_object.last_value = d
            param_object.save()
            print("param value updated")
        else:
            print("Not updating")
    except KeyError:
        print("Urk, error updating parameter value")
        pass

@database_sync_to_async
def get_param_object(dev_id, periph_id, param_id):
    try:
        param = models.Parameter.objects.filter(peripheral__periph_id=periph_id).filter(peripheral__device__dev_id=dev_id).get(param_id=param_id)
        return param
    except ObjectDoesNotExist:
        print("Invalid id")
        return None

@database_sync_to_async
def get_device_object(dev_id):
    try:
        dev = models.Device.objects.get(dev_id=dev_id)
        return dev
    except ObjectDoesNotExist:
        print("Invalid id")
        return None

@database_sync_to_async
def is_invalid_dev(dev_id):
    try:
        obj = models.Device.objects.get(dev_id=dev_id)
        return False
    except ObjectDoesNotExist:
        return True

@database_sync_to_async
def is_invalid_periph(dev_id, p_id):
    try:
        obj = models.Peripheral.objects.filter(device__dev_id=dev_id).get(periph_id=p_id)
        return False
    except ObjectDoesNotExist:
        return True
        
@database_sync_to_async
def is_invalid_param(d_id, p_id, prm_id):
    try:
        obj = models.Parameter.objects.filter(peripheral__periph_id=p_id).filter(peripheral__device__dev_id=d_id).get(param_id=prm_id)
        return False
    except ObjectDoesNotExist:
        return True

@database_sync_to_async
def is_existing_device(d_id):
    exists = False
    try:
        D = models.Device.objects.get(dev_id=d_id)
        exists = True
    except:
        exists = False
    return exists


@database_sync_to_async
def build_new_device(d_info: dict):
    success = True
    try:
        D = models.Device(
            name=d_info['name'],
            dev_id=d_info['dev_id'],
            last_polled=d_info['last_polled'],
            ip_address=d_info['ip_addr'],
            api_port=d_info['api_port'],
            cmd_url=d_info['cmd_url'],
            num_peripherals=d_info['periph_num'],
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
def build_new_peripheral(p_info):
    success = True

    try:
        D = models.Device.objects.get(dev_id=p_info['device'])

        P = models.Peripheral(
            periph_id=p_info['periph_id'],
            periph_type=p_info['periph_type'],
            device=D,
            name=p_info['name'],
            num_params=p_info['param_num'],
            sleep_state=0,
            is_powered=1,
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
def build_new_parameter(prm_info, dev_id):
    success = True

    try:
        Per = models.Peripheral.objects.filter(device__dev_id=dev_id).get(periph_id=prm_info['periph_id'])

        P = models.Parameter(
            param_id=prm_info['param_id'],
            peripheral=Per,
            name=prm_info['name'],
            max_value=prm_info['max_value'],
            data_type=prm_info['data_type'],
            is_getable=prm_info['is_gettable'],
            is_setable=prm_info['is_settable'],
            is_action=prm_info['is_action'],
            is_streamable=prm_info['is_streamable']
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


########################
#   build_request(data)
#   parses incomming json request
#   returns json string  
#   to relay & target or error response
########################
async def build_request(data):
    debug_print("Building request from:")
    debug_print(data)
    device_object = None
    param_object = None
    url = ""
    response = {}
    fail = False

    ## error check the request ## 
    if "cmd_type" not in data.keys():
        debug_print("Error: missing cmd_type")
        response = error_response(ERR_CODE_MISSING_FIELD)
        fail = True

    ## check correct keys ##
    if not fail:
        cmd_type = CommandTypeToInteger(data['cmd_type'])
        if not check_request_keys(cmd_type, data):
            response = error_response(ERR_CODE_MISSING_FIELD)
            fail = True

    ## check valid device/param/peripheral ##
    if not fail:
        if "dev_id" in data.keys():
            fail = await is_invalid_dev(data['dev_id'])
            if fail:
                response = error_response(ERR_CODE_INVALID_DEV_ID)
        elif "periph_id" in data.keys():
            fail = await is_invalid_periph(data['dev_id'], data['periph_id'])
            if fail:
                response = error_response(ERR_CODE_INVALID_PERIPH_ID)
        elif "param_id" in data.keys():
            fail = is_invalid_param(data['dev_id'], data['periph_id'], data['param_id'])
            if fail:
                response = error_response(ERR_CODE_INVALID_PARAM_ID)

    ## check a couple of other fail conditions ##
    if not fail:
        if cmd_type != CMD_TYPE_INFO and (data['dev_id'] == 0 or data['periph_id'] == 0 or data['param_id'] == 0): 
            response = error_response(ERR_CODE_INVALID_CMD_PARAMS)
            fail = True
        elif cmd_type == CMD_TYPE_SET and int(data['data']) > 0:
            p_obj = await get_param_object(data['dev_id'], data['periph_id'], data['param_id'])
            if p_obj == None or int(data['data']) > p_obj.max_value:
                response = error_response(ERR_CODE_INVALID_DATA_VALUE)
                fail = True
        elif cmd_type == CMD_TYPE_STREAM:
            if type(data['param_ids']) is not list or len(data['param_ids']) == 0:
                response = error_response(ERR_CODE_INVALID_JSON)
                fail = True
            else:
                for p in data['param_ids']:
                    if is_invalid_param(data['dev_id'], data['periph_id'], p):
                        response = error_response(ERR_CODE_INVALID_PARAM_ID)
                        fail = True
        elif cmd_type == CMD_TYPE_STREAM and int(data['rate']) > API_WEBSOCKET_MAX_RATE:
            response = error_response(ERR_CODE_INVALID_STREAM_RATE)
            fail = True

    ## everything should be checked by here ## 
    ## build the request
    if not fail:
        response['cmd_type'] = cmd_type
        if cmd_type == CMD_TYPE_INFO or cmd_type == CMD_TYPE_GET or cmd_type == CMD_TYPE_ACTION or cmd_type == CMD_TYPE_SET:
            response['periph_id'] = int(data['periph_id'])
            response['param_id'] = int(data['param_id'])
        if cmd_type == CMD_TYPE_SET:
            d_obj = await get_param_object(data['dev_id'], data['periph_id'], data['param_id'])
            response['data_type'] = int(d_obj.data_type)
            response['data'] = int(data['data'])
        if cmd_type == CMD_TYPE_STREAM:
            response['rate'] = int(data['rate'])
            response['ext'] = int(data['ext'])
            response['param_ids'] = int(data['param_ids'])
            response['periph_id'] = int(data['periph_id'])

        device_object = await get_device_object(data['dev_id'])

        url = "http://"
        url += device_object.ip_address
        url += ":"
        url += str(device_object.api_port)
        if not device_object.cmd_url.startswith("/"):
            url += "/"
        url += device_object.cmd_url


    ret = (fail, response, url)
    debug_print(f"build request returning Fail={fail} response={response} url={url}")
    
    return ret



class CommandConsumer(AsyncWebsocketConsumer):

    def __init__(self, **kwargs):
        super().__init__()
        

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        fail, rq, url = await build_request(data)
        
        ## if fail, return error message ##
        if fail == True:
            await self.send(json.dumps(rq))
        else:
            ## send the external http request ##
            print("sending")
            print(rq)
            result, response = await ext_http_post(url, rq)
            if result != HTTP_RSP_AQUIRED:
                response = error_response(result)
            else:
                if response['rsp_type'] == RSP_TYPE_DATA:
                    param = await get_param_object(data['dev_id'], response['periph_id'], response['param_id'])
                    if param != None:
                        print("updating")
                        await update_parameter(response['data'], param)
            
            await self.send(json.dumps(response))



class LedCtrlConsumer(AsyncWebsocketConsumer):

    async def websocket_receive(self, message):

        

        return super().websocket_receive(message)



##
#   Discoverer  - the websocket consumer for the discover & enumerate functionality
#
class Discoverer(AsyncWebsocketConsumer):

    def build_url(self, target, port, ext):
        url = "http://"
        url += target
        url += ":"
        url += str(port)
        if(ext[0] != "/"):
            url+="/"
        url += ext

        return url

    ## Websocket receive ##
    async def receive(self, text_data):
        
        data = json.loads(text_data)
        try:
            target = data['ip_addr']
            ext = data['extension']
            port = data['port']
        except KeyError:
            print("missing initial data")
            await self.send(json.dumps({"data": "Error: Missing initial data"}))
            return

        await self.send(json.dumps({"data": f"> Enumerating device at [{target}]", "code": 1}))

        await self.enumerate_device(target, port, ext)


    ## Enumerate the device at target:port/extension
    async def enumerate_device(self, target, port, ext):
        """ 
            Send sequential/recursive info requests
            Create a nested data structure from responses
            Store the new device in database
        """
        fail = False
        url = self.build_url(target, port, ext)

        await self.send(json.dumps({"data": "Starting........****", "code": 200 }))
        await self.send(json.dumps({"data": f"Enumerating Device at {url}", "code": 200 }))

        # use the new packet class! # 
        devInfo = DevInfoPacket(url)
        res_d, rsp_d = await devInfo.send_request()
        
        ## Do safety dance
        if res_d != HTTP_RSP_AQUIRED:
            await self.send(json.dumps(error_response(res_d)))
            fail = True
        else:
            device_data = {
                "name": devInfo.get_response_value("name"),
                "periph_num": devInfo.get_response_value("periph_num"),
                "dev_id": devInfo.get_response_value("dev_id"),
                "last_polled": datetime.now(),
                "ip_addr": target,
                "api_port": int(port),
                "cmd_url": ext,
                "sleep_state": 0,
                "is_powered": True,
                "setup_date": datetime.now(),
                "peripherals": [],
            }
            await self.send(json.dumps({"data": f"> Device {device_data['name']} [id: {hex(device_data['dev_id'])}]", "code": 200 }))

            ## recusively get info about peripherals
            for p in devInfo.get_periph_ids():
                periphInfo = PeriphInfoPacket(url, p)
                res_p, rsp_p = await periphInfo.send_request()
                ## Do safety dance
                if res_p != HTTP_RSP_AQUIRED:
                    await self.send(json.dumps(error_response(res_p)))
                    fail = True
                else:
                    periph_data = {
                        "device": device_data["dev_id"],
                        "periph_id": periphInfo.get_response_value("periph_id"),
                        "name": periphInfo.get_response_value("name"),
                        "param_num": periphInfo.get_response_value("param_num"),
                        "param_ids": periphInfo.get_param_ids(),
                        "periph_type": periphInfo.get_response_value("periph_type"),
                        "sleep_state": 0,
                        "parameters": [],
                    }
                    await self.send(json.dumps({"data": f">> Peripheral {periph_data['name']} [id: {hex(periph_data['periph_id'])}]", "code": 200 }))

                    ## recusively get info about parameters
                    for prm in periphInfo.get_param_ids():
                        paramInfo = ParamInfoPacket(url, p, prm)
                        res_prm, rsp_prm = await periphInfo.send_request()
                        ## Da da Da da DaDa Da Da Da Safety Dance
                        if res_prm != HTTP_RSP_AQUIRED:
                            await self.send(json.dumps(error_response(res_prm)))
                            fail = True
                        else: 
                            param_data = {
                                "name": paramInfo.get_response_value("param_name"),
                                "periph_id": periph_data["periph_id"],
                                "param_id": paramInfo.get_response_value("param_id"),
                                "param_type": 0,
                                "methods": paramInfo.get_response_value("methods"),
                                "max_value": paramInfo.get_response_value("param_max"),
                                "data_type": paramInfo.get_response_value("data_type"),
                            }
                            print(param_data)
                            await self.send(json.dumps({"data": f">>> Parameter {param_data['name']} [id: {hex(param_data['param_id'])}]", "code": 200 }))
                            periph_data["parameters"].append(param_data)

                    device_data["peripherals"].append(periph_data)

        if not fail:
            await self.send(json.dumps({"data": " Device succesfully enumerated", "code": 200 }))
            await self.send(json.dumps({"data": " Engaging database... standby", "code": 200 }))
        else:
            await self.send(json.dumps({"data": "Device enumeration failed :(", "code": 506 }))

        # store the items
        if not fail:

            result = await build_new_device(device_data)
            if not result:
                await self.send(json.dumps({"data": "- - - failed when creating new Device", "code": 506}))
                fail = True
            else:
                await self.send(json.dumps({"data": "- - - Created new Device [id]", "code": 201}))
                
            if not fail:

                for periph in device_data["peripherals"]:
                    result = await build_new_peripheral(periph)
                    if not result:
                        await self.send(json.dumps({"data": "- - - failed when creating new peripheral", "code": 506}))
                        fail = True
                    else:
                        await self.send(json.dumps({"data": "- - - Created new Peripheral [id]", "code": 201}))
                
                    for param in periph["parameters"]:
                        param['is_gettable']    = ((param['methods'] & API_GET_MASK) > 0) if param['methods'] is not None else 0
                        param['is_settable']    = ((param['methods'] & API_SET_MASK) > 0) if param['methods'] is not None else 0
                        param['is_action']      = ((param['methods'] & API_ACT_MASK) > 0) if param['methods'] is not None else 0
                        param['is_streamable']  = ((param['methods'] & API_STREAM_MASK) > 0) if param['methods'] is not None else 0

                        result = await build_new_parameter(param, periph["device"])
                        if not result:
                            await self.send(json.dumps({"data": "- - - failed when creating new parameter", "code": 506}))
                            fail = True
                        else:
                            await self.send(json.dumps({"data": "- - - Created new Parameter [id]", "code": 201}))

        if not fail:
            await self.send(json.dumps({"data": "Succesfully enumerated Device!", "code": 201}))
        else:
            await self.send(json.dumps({"data": "Failed to Enumerate Device :(", "code": 506 }))
   



class DeviceStream(AsyncWebsocketConsumer):
    """ this consumer hosts the websocket for the device to connect to
    """

    async def websocket_connect(self, message):
        print("Got connection!")
        await self.channel_layer.group_add("stream", self.channel_name)
        return super().websocket_connect(message)

    async def websocket_receive(self, message):
        return super().websocket_receive(message)

    async def websocket_disconnect(self, message):
        return super().websocket_disconnect(message)



class ClientStream(AsyncWebsocketConsumer):

    """ plan for streamer... 
        - want client to select streaming parameters then open up a websocket to this page
        - start a websocket server
        - send http request to the device requesting a stream
        - wait for ok response 
        - Device will connect to DeviceStream
        - add client to a channel-layer
        - ideally route traffic as low-effort as possible between device & client
        - deal with cleanup, etc.
    """


    async def websocket_connect(self, message):
        """ add the client to the channel layer? 
            send the http request to the device
        """
        fail = False
        device = None
        periph = None
        stream_params = []

        error_rsp = {
            "message": "",
            "error_code": 0,
        }

        expected_keys = [
            ("periph_id", int),
            ("param_ids", list),
            ("rate", int),
            ("host", str),
        ]

        ## Whole heap a error checking - JSON first ##
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            print("Error decoding json")
            fail = True
            error_rsp['message'] = "Malformed Json Request"
            error_rsp['error_code'] = ERR_CODE_INVALID_JSON
        
        ## check keys/keytypes ##
        if not fail:
            badkeys, missingkeys = check_json_errors(data, expected_keys)

            if len(badkeys) > 0:
                error_rsp['message'] = f"Invalid field type: {badkeys[0]}"
                error_rsp['error_code'] = ERR_CODE_INVALID_JSON
                fail = True
            elif len(missingkeys) > 0:
                error_rsp['message'] = f"Missing field: {missingkeys[0]}"
                error_rsp['error_code'] = ERR_CODE_INVALID_JSON
                fail = True

        # check param ID len ##
        if not fail:
            if len(data['param_ids']) < 1:
                error_rsp['message'] = f"No parameter IDs supplied"
                error_rsp['error_code'] = ERR_CODE_INVALID_JSON
                fail = True
        
        ## check rate ##
        if not fail:
            if data['rate'] not in API_WEBSOCKET_RATES:
                error_rsp['message'] = f"Invalid rate"
                error_rsp['error_code'] = ERR_CODE_INVALID_JSON
                fail = True          

        ## get device ##
        if not fail:
            device = await get_device_object(data['dev_id'])
            
            if device == None:
                error_rsp['message'] = f"Missing field: {missingkeys[0]}"
                error_rsp['error_code'] = ERR_CODE_INVALID_DEV_ID
                fail = True

        ## get peripheral ##
        if not fail:
            periph = await self.get_peripheral_object(data['dev_id'], data['periph_id'])
            if periph == None:
                error_rsp['message'] = f"Invalid Peripheral ID"
                error_rsp['error_code'] = ERR_CODE_INVALID_PERIPH_ID
                fail = True              

        ## get parameters ##
        if not fail:
            for param_id in data['param_ids']:

                param = await get_param_object(data['dev_id'], data['periph_id'], param_id)

                if param == None:
                    error_rsp['message'] = f"Invalid Parameter ID: {param_id}"
                    error_rsp['error_code'] = ERR_CODE_INVALID_PARAM_ID
                    fail = True
                elif param.is_streamable == False:
                    error_rsp['message'] = f"Parameter {param.name} is not streamable"
                    error_rsp['error_code'] = ERR_CODE_INVALID_REQUEST
                    fail = True   
                else:
                    stream_params.appen(param)

        ## send the http stream request ##
        if not fail:
            print("Sending request for websocket connection")
            request = {
                'periph_id': periph.periph_id,
                'param_ids': [x.param_id for x in stream_params],
                'rate': data['rate'],
                'ext': API_WEBSOCKET_INCOMMING_STREAM_EXTENSION
            }

            url = "http://" + \
                device.ip_address +\
                ":" + \
                str(device.port) + \
                device.cmd_url

            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(url, json=request) as rsp:
                        status = rsp.status
                        await self.send(json.dumps({"data": "> Got response to stream request [" + str(status) + "]", "code": status}))
                        data = await rsp.json()
                        ## check for correct response from the device ##
                        if "rsp_type" in data.keys() and data["rsp_type"] == RSP_TYPE_OK:
                            print("Got a success response from the device")
                        
            except aiohttp.ClientConnectionError:
                await self.send(json.dumps({"message": "Error: Device is unnreachable!", "code": 504}))
                fail = True
            except aiohttp.InvalidURL:
                await self.send(json.dumps({"message": "Error: Invalid URL!"}))
                fail = True

        if not fail:
            print("Device should be connecting to streaming component right about now...")

        if not fail:
            ## check this works!
            Clients.objects.create(channel_name="stream")
            await self.channel_layer.group_add("stream", self.channel_name)

        return super().websocket_connect(message)

    # async def receive(self, text_data=None, bytes_data=None):
    #     print("got message")
    #     if bytes_data is not None:
    #         bytestring = bytes_data.decode("utf-8")
    #         print(bytestring)
    #     elif text_data is not None:
    #         print(text_data)
    #     else:
    #         print("no data")
    #     return super().receive(text_data=text_data, bytes_data=bytes_data)

    async def websocket_receive(self, message):
        return super().websocket_receive(message)

    async def websocket_send(self, text_data=None, bytes_data=None, close=False):
        return super().send(text_data=text_data, bytes_data=bytes_data, close=close)

    async def websocket_disconnect(self, message):
        Clients.objects.filter(channel_name="stream").delete()
        return super().websocket_disconnect(message)
    




    # async def courier(self):
    #     """ this task acts as bridge between device and establishes a websocket server listening on 
    #         configured port. 
    #         Client connects to the websocket, prompting this task's creation
    #         Connect coroutine sends the stream request to the Device
    #         courier begins a websocket server 
    #         Device connects to the websocket server & commences sending data
    #         routed to the client via self.send
    #     """

