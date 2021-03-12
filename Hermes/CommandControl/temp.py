
from Hermes.CommandControl.command_api import *


class Discoverer(AsyncWebsocketConsumer):

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

    def build_url(self, target, port, ext):
        url = "http://"
        url += target
        url += ":"
        url += str(port)
        if(ext[0] != "/"):
            url+="/"
        url += ext

        return url

    async def enumerate_device(self, target, port, ext):
        """ 
            Send sequential/recursive info requests
            Create a nested data structure from responses
            Store the new device in database
        """
        fail = False
        url = self.build_url(target, port, ext)

        # use the new packet class! # 
        devInfo = DevInfoPacket(url)
        res_d, rsp_d = await devInfo.send_request()
        
        ## Do safety dance
        if res_d != HTTP_RSP_AQUIRED:
            await self.send(json.dumps(error_response(res)))
            fail = True
        else:
            device_data = {
                "name": devInfo.get_response_value("name"),
                "peirph_num": devInfo.get_response_value("periph_num"),
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

            ## recusively get info about peripherals
            for p in devInfo.get_periph_ids():
                periphInfo = PeriphInfoPacket(url, p)
                res_p, rsp_p = await periphInfo.send_request()
                ## Do safety dance
                if res_p != HTTP_RSP_AQUIRED:
                    await self.send(json.dumps(error_response(res)))
                    fail = True
                else:
                    periph_data = {
                        "device": device_data["dev_id"],
                        "periph_id": periphInfo.get_response_value("periph_id"),
                        "name": periphInfo.get_response_value("name"),
                        "param_num": periphInfo.get_response_value("param_num"),
                        "param_ids": periphInfo.get_param_ids(),
                        "periph_type": periphInfo.get_response_value("periph_type"),
                        "parameters": [],
                    }

                    ## recusively get info about parameters
                    for prm in periphInfo.get_param_ids():
                        paramInfo = ParamInfoPacket(url, p, prm)
                        res_prm, rsp_prm = await periphInfo.send_request()
                        ## Da da Da da DaDa Da Da Da Safety Dance
                        if res_prm != HTTP_RSP_AQUIRED:
                            await self.send(json.dumps(error_response(res)))
                            fail = True
                        else: 
                            param_data = {
                                "name": paramInfo.get_response_value("name"),
                                "periph_id": periph_data["periph_id"],
                                "param_id": paramInfo.get_response_value("param_id"),
                                "param_type": 0,
                                "methods": paramInfo.get_response_value("methods"),
                                "max_value": paramInfo.get_response_value("param_max"),
                                "data_type": paramInfo.get_response_value("data_type"),
                            }

                            periph_data["parameters"].append(param_data)

                    device_data["peripherals"].append(periph_data)

        if not fail:
            await self.send(json.dumps({"data": " Device succesfully enumerated", "code": 200 }))
            await self.send(json.dumps({"data": " Engaging database... standby", "code": 200 }))
        else:
            await self.send(json.dumps({"data": "Device enumeration failed :(", "code": 506 }))

        # store the items
        if not fail:
            for periph in device_data["peripherals"]:
                for param in periph["parameters"]:
                    param['is_gettable']    = ((param['methods'] & API_GET_MASK) > 0)
                    param['is_settable']    = ((param['methods'] & API_SET_MASK) > 0)
                    param['is_action']      = ((param['methods'] & API_ACT_MASK) > 0)
                    param['is_streamable']  = ((param['methods'] & API_STREAM_MASK) > 0)

                    result = await build_new_parameter(param, periph["device"])
                    if not result:
                        await self.send(json.dumps({"data": "- - - failed when creating new parameter", "code": 506}))
                        fail = True
                    else:
                        await self.send(json.dumps({"data": "- - - Created new Parameter [id]", "code": 201}))
                if not fail:
                    result = await build_new_peripheral(periph)
                    if not result:
                        await self.send(json.dumps({"data": "- - - failed when creating new peripheral", "code": 506}))
                        fail = True
                    else:
                        await self.send(json.dumps({"data": "- - - Created new Peripheral [id]", "code": 201}))
            if not fail:
                result = await build_new_device(device_data)
                if not result:
                    await self.send(json.dumps({"data": "- - - failed when creating new Device", "code": 506}))
                    fail = True
                else:
                    await self.send(json.dumps({"data": "- - - Created new Device [id]", "code": 201}))

        if not fail:
            await self.send(json.dumps({"data": "Succesfully enumerated Device!", "code": 201}))
        else:
            await self.send(json.dumps({"data": "Failed to Enumerate Device :(", "code": 506 }))
   
