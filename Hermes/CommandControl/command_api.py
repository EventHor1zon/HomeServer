

ERR_CODE_INVALID_RESPONSE_LEN = 0x1e
ERR_CODE_INVALID_JSON = 0x1f

ERR_CODE_MISSING_FIELD = 0x0d
ERR_CODE_INVALID_CMD_PARAMS = 0x0f

ERR_CODE_INVALID_DEV_ID = 0x2a
ERR_CODE_INVALID_PERIPH_ID = 0x2b
ERR_CODE_INVALID_PARAM_ID = 0x2c

CMD_TYPE_INFO = 0x00
CMD_TYPE_GET = 0x01
CMD_TYPE_SET = 0x02
CMD_TYPE_ACTION = 0x04
CMD_TYPE_STREAM = 0x05


RSP_TYPE_INFO = 0x00
RSP_TYPE_OK = 0x01
RSP_TYPE_DATA = 0x02
RSP_TYPE_ERR = 0x03
RSP_TYPE_STREAM = 0x04

API_GET_MASK = 1
API_SET_MASK = 2
API_ACT_MASK = 4

base_keys = ["cmd_type", "periph_id", "param_id", "dev_id"]
set_keys = ["cmd_type", "periph_id", "param_id", "dev_id", "data"]



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


def check_set_keys(request):
    for key in set_keys:
        if key not in request.keys():
            return False
    return True



def check_basic_keys(request):
    for key in base_keys:
        if key not in request.keys():
            return False
    return True
