# HomeServer
Django server for interraction with ESP_Home system


#### Pages
- Index: shows server uptime & details
- Discover: Add new devices using ip, port & http url extension
- LedControl: RGB colour picker and led strip selector
- Stream: *new!* page for streaming data to graph - wip
- Device: Individual pages for devices, lists peripherals
- Peripheral: gets/sets/actions for peripheral parameters


#### Info

Uses Django and Django channels for async websocket communications.
Communications between client and server are handled with websockets,
whilst commands to connected devices are handled by http requests using custom api

**TODO** make an api map!

Django maintains a database of devices, peripherals and parameters. Each device has children peripherals,
and each peripheral has children parameters. This way, the real strength of this api/server combo can be harnessed:
The user can remotely control every parameter of every peripheral attached to a device!

This, when coupled with the __fully armed and operational streaming interface__ (slight exageration) then the 
device can be manipulated, and the results watched in real time.

#### Issues/Things to do next

- Unstable Streaming: this will get fixed, soon! Some unstable asyncio stuff
- Too dependent on dictionaries?
- Investigate using request classes like those implemented in CommandAPI.py
- HTML unfinished - make use of those side-panels!
- Server - Get a running ASGI server, preferably better DB
- Data Logging - To Do: Soon, etc!
