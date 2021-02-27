

ERR_CODE_RSP_INVJSON = 0x30
ERR_CODE_HTTP_TIMEOUT = 0x31
ERR_CODE_INV_URL = 0x32
ERR_CODE_INVALID_RESPONSE_LEN = 0x1e
ERR_CODE_INVALID_JSON = 0x1f
ERR_CODE_MISSING_FIELD = 0x0d
ERR_CODE_INVALID_CMD_PARAMS = 0x0f
ERR_CODE_INVALID_DEV_ID = 0x2a
ERR_CODE_INVALID_PERIPH_ID = 0x2b
ERR_CODE_INVALID_PARAM_ID = 0x2c
ERR_CODE_INVALID_REQUEST = 0x2e
ERR_CODE_INVALID_DATA_VALUE = 0x2f
ERR_CODE_INVALID_DATA_TYPE = 0x29
ERR_CODE_INVALID_STREAM_RATE = 0x28

CMD_TYPE_INFO = 0x00
CMD_TYPE_GET = 0x01
CMD_TYPE_SET = 0x02
CMD_TYPE_ACTION = 0x04
CMD_TYPE_STREAM = 0x05


RSP_TYPE_INFO = 0x00
RSP_TYPE_OK = 0x01
RSP_TYPE_ERR = 0x02
RSP_TYPE_DATA = 0x03
RSP_TYPE_STREAM = 0x04

API_GET_MASK = 1
API_SET_MASK = 2
API_ACT_MASK = 4
API_STREAM_MASK = 8

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


base_keys = ["periph_id", "param_id"]
info_keys = base_keys.append("dev_id")
get_keys = base_keys.append("dev_id")
act_keys = base_keys.append("dev_id")
data_keys = base_keys.extend(["data", "data_t"])
set_keys = base_keys.extend(["data", "data_t"]) # check this data t is needed
stream_keys =  ["dev_id", "periph_id", "param_ids", "rate", "ext"]
err_keys = ["error_code", "msg"]

API_WEBSOCKET_RATE_1HZ = 0
API_WEBSOCKET_RATE_5HZ = 1
API_WEBSOCKET_RATE_10HZ = 2

API_WEBSOCKET_MAX_RATE = API_WEBSOCKET_RATE_10HZ

API_WEBSOCKET_RATES = [
    API_WEBSOCKET_RATE_1HZ,
    API_WEBSOCKET_RATE_5HZ,
    API_WEBSOCKET_RATE_10HZ,
]


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
    if cmd_t == CMD_TYPE_INFO:
        keys = info_keys
    elif cmd_t == CMD_TYPE_GET:
        keys = get_keys
    elif cmd_t == CMD_TYPE_SET:
        keys = set_keys
    elif cmd_t == CMD_TYPE_ACTION:
        keys = act_keys
    elif cmd_t == CMD_TYPE_STREAM:
        keys = stream_keys
    else:
        return False
    
    for key in keys:
        if key not in req.keys():
            print("missing " + key)
            return False
    return True

def check_response_keys(rsp_t, rsp):
    if rsp_t == RSP_TYPE_INFO:
        keys = base_keys
    elif rsp_t == RSP_TYPE_DATA:
        keys = data_keys
    elif rsp_t == RSP_TYPE_ERR:
        keys = err_keys
    elif rsp_t == RSP_TYPE_OK:
        return True
    else:
        return False
    
    for key in keys:
        if key not in rsp.keys():
            print("missing " + key)
            return False
    return True
 


def check_set_keys(request):
    print(request)
    for key in set_keys:
        if key not in request.keys():
            print("missing " + key)
            return False
    return True


def check_info_keys(req):
    for key in info_keys:
        if key not in req.keys():
            return False
    return True

def check_basic_keys(request):
    for key in base_keys:
        if key not in request.keys():
            return False
    return True
