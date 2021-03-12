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


    async def enumerate_device(self, target, port, extension):
        
        url = "http://"
        url += target
        url += ":"
        url += str(port)
        if(extension[0] != "/"):
            url+="/"
        url += extension
        fail = False