
import json
import aiohttp

## Error codes 
# client side errors
ERR_CODE_MISSING_FIELD          = 0x01
ERR_CODE_INVALID_JSON           = 0x02
# request content errors
ERR_CODE_INVALID_CMD_PARAMS     = 0x10
ERR_CODE_INVALID_STREAM_RATE    = 0x11
ERR_CODE_INVALID_DATA_TYPE      = 0x12
ERR_CODE_INVALID_DEV_ID         = 0x13
ERR_CODE_INVALID_PERIPH_ID      = 0x14
ERR_CODE_INVALID_PARAM_ID       = 0x15
ERR_CODE_INVALID_REQUEST        = 0x16
ERR_CODE_INVALID_DATA_VALUE     = 0x17
# http errors
ERR_CODE_INVALID_URL            = 0x22
ERR_CODE_HTTP_TIMEOUT           = 0x23
# response errors
ERR_CODE_INVALID_RSP_JSON       = 0x30
ERR_CODE_INVALID_RSP_LEN        = 0x31
ERR_CODE_ERROR_RESPONSE         = 0x32

## HTTP response status codes
HTTP_RSP_AQUIRED = 0
HTTP_RSP_NOT_AQUIRED = 0xFF

## API command types
CMD_TYPE_INFO = 0x00
CMD_TYPE_GET = 0x01
CMD_TYPE_SET = 0x02
CMD_TYPE_ACTION = 0x04
CMD_TYPE_STREAM = 0x05

## API response types
RSP_TYPE_INFO = 0x00
RSP_TYPE_OK = 0x01
RSP_TYPE_ERR = 0x02
RSP_TYPE_DATA = 0x03
RSP_TYPE_STREAM = 0x04

## API method bits
API_GET_MASK = 1
API_SET_MASK = 2
API_ACT_MASK = 4
API_STREAM_MASK = 8

## API parameter data types
PARAMTYPE_NONE = 0
PARAMTYPE_INT8 = 1
PARAMTYPE_UINT8 = 1
PARAMTYPE_INT16 = 2
PARAMTYPE_UINT16 = 2
PARAMTYPE_INT32 = 4
PARAMTYPE_UINT32 = 4
PARAMTYPE_FLOAT = 5
PARAMTYPE_DOUBLE = 8
PARAMTYPE_STRING = 0x0A
PARAMTYPE_BOOL = 0x0B
PARAMTYPE_INVALID = 0xFF

## API parameter types
PTYPE_ADDR_LEDS = 0x01
PTYPE_STD_LED = 0x02    
PTYPE_ACCEL_SENSOR = 0x03
PTYPE_ENVIRO_SENSOR = 0x04
PTYPE_DISTANCE_SENSOR = 0x05
PTYPE_POWER_SENSOR = 0x06
PTYPE_ADC = 0x07                      #/** < adc periperal (on board) */
PTYPE_IO = 0x08                       #/** < basic io function */
PTYPE_DISPLAY = 0x09          #/** < display oled/led/epaper */
PTYPE_COMMS = 0x0A            #/** < a comms/bluetooth/radio */
PTYPE_NONE = 0xFF       #/** < blank **/

## API websocket rates
API_WEBSOCKET_RATE_1HZ = 0
API_WEBSOCKET_RATE_5HZ = 1
API_WEBSOCKET_RATE_10HZ = 2

API_WEBSOCKET_MAX_RATE = API_WEBSOCKET_RATE_10HZ

API_WEBSOCKET_RATES = [
    API_WEBSOCKET_RATE_1HZ,
    API_WEBSOCKET_RATE_5HZ,
    API_WEBSOCKET_RATE_10HZ,
]

base_keys = ["dev_id", "periph_id"]
dev_info_rsp_keys = ["rsp_type", "name", "periph_ids", "periph_num", "dev_id"]
periph_info_rsp_keys = ["rsp_type", "name", "periph_id", "param_ids", "param_num", "periph_type"]
param_info_rsp_keys = ["rsp_type", "param_name", "periph_id", "param_id", "methods", "param_max", "data_type"]
ok_rsp_keys = ["rsp_type", "periph_id", "param_id"]
get_keys = ["rsp_type","dev_id", "periph_id", "param_id"]
get_rsp_keys = ["rsp_type", "param_id", "periph_id", "data", "data_type"]
act_keys = ["dev_id", "periph_id", "param_id"]
set_keys = ["dev_id", "periph_id", "param_id", "data", "data_type"] # check this data t is needed
stream_keys =  ["dev_id", "periph_id", "param_ids", "rate", "ext"]
err_keys = ["error_code", "msg"]

## Error response messages
error_messages = {
    ERR_CODE_INVALID_RSP_JSON: "Invalid JSON in device response",
    ERR_CODE_HTTP_TIMEOUT: "Device response timed out",
    ERR_CODE_INVALID_URL: "Device URL is invalid",
    ERR_CODE_INVALID_RSP_LEN: "Response length is invalid",
    ERR_CODE_INVALID_JSON: "Invalid json in request",
    ERR_CODE_MISSING_FIELD: "Missing field in request",
    ERR_CODE_INVALID_CMD_PARAMS: "Invalid command parameters",
    ERR_CODE_INVALID_DEV_ID: "Invalid device ID",
    ERR_CODE_INVALID_PERIPH_ID: "Invalid peripheral ID",
    ERR_CODE_INVALID_PARAM_ID: "Invalid parameter ID",
    ERR_CODE_INVALID_REQUEST: "Invalid request type",
    ERR_CODE_ERROR_RESPONSE: "Device returned an error",
}





DEBUG = 1



def debug_print(msg):
    if DEBUG == 1:
        print(msg)




#######################
##  class RequestPacket
#   \brief          - a request class base to make API requests a little easier
#   \param url      - the url for the request 
#   \param cmd_type - the command type code
#   \periph_id      - the peripheral id
#   \param_id       - the parameter id
class RequestPacket():

    ''' a dict holding the json k/v pairs '''
    fields = {}
    response_status = HTTP_RSP_NOT_AQUIRED
    response = {}
    expected_rsp_t = 0xFF
    expected_rsp_keys = []

    ''' set the provided cmd type & url '''
    def __init__(self, url, cmd_type, periph_id, param_id):
        self.fields["cmd_type"] = int(cmd_type)
        self.fields["param_id"] = int(param_id)
        self.fields["periph_id"] = int(periph_id)
        self.url = url

    ''' return the fields as a string '''  
    def dump_string(self):
        return json.dumps(self.fields)

    ''' return the fields as a dict '''
    def pkt_dict(self):
        return self.fields

    ''' send the json fields to the url & return response/status '''
    async def send_request(self):

        result = 0
        response_data = {}
        debug_print(f"posting data to {self.url}")
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(self.url, json=self.fields) as rsp:
                    response_data = await rsp.json()
                    debug_print("sent")
                    debug_print(self.dump_string())
                    debug_print(f"Got response: (status: {rsp.status})")
                    debug_print(response_data)
                    result = HTTP_RSP_AQUIRED
                    self.response_status = result
                    self.response.update(response_data)
        except json.JSONDecodeError:
            result = ERR_CODE_INVALID_RSP_JSON
        except aiohttp.ClientTimeout:
            result = ERR_CODE_HTTP_TIMEOUT
        except aiohttp.InvalidURL:
            result = ERR_CODE_INVALID_URL

        return result, response_data


    ''' get the response status ''' 
    def get_response_status(self):
        return self.response_status
    
    ''' get the response dict, None if no reponse '''
    def get_response(self):
        return self.response

    ''' get a response field value '''
    def get_response_value(self, key):
        if len(self.response) == 0:
            debug_print("Response is empty")
            return None
        elif not self.check_response_key(key):
            return None
        else:
            return self.response[key]

    ''' check for key in response '''
    def check_response_key(self, key: str):
        if len(self.response) == 0:
            debug_print("Response is empty")
            return False
        elif key in self.response.keys():
            debug_print(f"Found key {key}")
            return True
        else:
            debug_print(f"did not find key {key}")
            return False

    ''' check for a list of keys in response '''
    def check_response_keys(self, keys: list):
        for key in keys:
            if not self.check_response_key(key):
                return False
            else:
                return True

    ''' checks response is expected response '''
    def check_expected_response(self):
        if len(self.response) == 0:
            return HTTP_RSP_NOT_AQUIRED
        elif not self.check_expected_response_type():
            try:
                if self.response['rsp_type'] == RSP_TYPE_ERR:
                    return ERR_CODE_ERROR_RESPONSE
            except:
                return ERR_CODE_INVALID_RSP_JSON
        if not self.check_response_keys(self.expected_rsp_keys):
            return ERR_CODE_INVALID_RSP_JSON
        return HTTP_RSP_AQUIRED

    ''' check the response rsp_type matches expected '''
    def check_expected_response_type(self):
        try:
            if response == None:
                return False
            elif self.response['rsp_type'] == self.expected_rsp_t:
                return True
        except KeyError:
            return False

##################################
## parent class for an info request
class InfoPacket(RequestPacket):

    def __init__(self, url, periph_id, param_id):
        self.expected_rsp_t = RSP_TYPE_INFO
        super().__init__(url, CMD_TYPE_INFO, periph_id, param_id)


class DevInfoPacket(InfoPacket):

    def __init__(self, url):
        self.expected_rsp_keys = dev_info_rsp_keys
        super().__init__(url, 0, 0)

    def get_periph_ids(self):
        if self.response == None:
            return []
        else:
            return self.response["periph_ids"]


class PeriphInfoPacket(InfoPacket):

    def __init__(self, url, periph_id: int):
        self.expected_rsp_keys = periph_info_rsp_keys
        super().__init__(url, periph_id, 0)

    def get_param_ids(self):
        if self.response == None:
            return []
        else:
            return self.response["param_ids"]


class ParamInfoPacket(InfoPacket):

    def __init__(self, url, periph_id, param_id):
        self.expected_rsp_keys = param_info_rsp_keys
        super().__init__(url, periph_id, param_id)


class ParamGetPacket(RequestPacket):

    def __init__(self, url, periph_id, param_id):
        self.expected_rsp_keys = get_rsp_keys
        super().__init__(url, CMD_TYPE_GET, periph_id, param_id)


class ParamSetPacket(RequestPacket):

    def __init__(self, url, periph_id, param_id, data, data_t):
        self.fields["data_type"] = int(data_t)
        if data_t == PARAMTYPE_BOOL:
            self.fields["data"] = True if data else False
        elif data_t == PARAMTYPE_STRING:
            self.fields["data"] = str(data)
        elif data_t == PARAMTYPE_FLOAT:
            self.fields["data"] = float(data)
        else:
            self.fields["data"] = int(data)
        self.expected_rsp_keys = ok_rsp_keys
        super().__init__(url, CMD_TYPE_SET, periph_id, param_id)

            

class ParamActionPacket(RequestPacket):

    def __init__(self, url, periph_id, param_id):
        self.expected_rsp_keys = ok_rsp_keys
        super().__init__(url, CMD_TYPE_ACTION, periph_id, param_id)



def CommandTypeToInteger(cmd):
    retval = 0xFF
    
    if cmd.upper() == "INFO":
        retval = 0
    elif cmd.upper() == "GET":
        retval = 1
    elif cmd.upper() == "SET":
        retval = 2
    elif cmd.upper() == "ACT":
        retval = 4
    elif cmd.upper() == "STREAM":
        retval = 5

    return retval



## @brief: Checks the request json dictionary for the correct keys 
#  @param cmd_t the command type as an integer
#  @param req   the request dictionary
def check_request_keys(cmd_t, req):
    # if cmd_t == CMD_TYPE_INFO:
    #     keys = info_keys
    # elif cmd_t == CMD_TYPE_GET:
    #     keys = get_keys
    # elif cmd_t == CMD_TYPE_SET:
    #     keys = set_keys
    # elif cmd_t == CMD_TYPE_ACTION:
    #     keys = act_keys
    # elif cmd_t == CMD_TYPE_STREAM:
    #     keys = stream_keys
    # else:
    #     return False
    # print(keys)
    # print(req.keys())
    # for key in keys:
    #     if key not in req.keys():
    #         print("missing " + key)
    #         return False
    return True

def check_response_keys(rsp_t, rsp):
    # keys = []
    # if rsp_t == RSP_TYPE_INFO:
    #     keys = base_keys
    # elif rsp_t == RSP_TYPE_DATA:
    #     keys = data_keys
    # elif rsp_t == RSP_TYPE_ERR:
    #     keys = err_keys
    # elif rsp_t == RSP_TYPE_OK:
    #     return True
    # else:
    #     return False
    
    # for key in keys:
    #     if key not in rsp.keys():
    #         print("missing " + key)
    #         return False
    return True
 


def check_set_keys(request):
    # print(request)
    # for key in set_keys:
    #     if key not in request.keys():
    #         print("missing " + key)
    #         return False
    return True


def check_info_keys(req):
    # for key in info_keys:
    #     if key not in req.keys():
    #         return False
    return True

def check_basic_keys(request):
    # for key in base_keys:
    #     if key not in request.keys():
    #         return False
    return True
