#!/usr/bin/env python3

"""
DBus adapter enabling desktop environments to control TUXEDO power profiles via the freedesktop power-profiles dbus interface

TODO:
    - implement polkit
    - tccd support profile hold?
    - add full set of ppd dbus api
"""

import asyncio
import json

from dbus_next.aio import MessageBus
from dbus_next import BusType, Variant
from dbus_next.service import ServiceInterface, dbus_property, PropertyAccess

import builtins
import functools
print = functools.partial(builtins.print, flush=True)

# ---- tccd DBus ----
TCCD_BUS = "com.tuxedocomputers.tccd"
TCCD_PATH = "/com/tuxedocomputers/tccd"
TCCD_INTERFACE = "com.tuxedocomputers.tccd"

# ---- PowerProfiles API ----s
BUS_NAME = "org.freedesktop.UPower.PowerProfiles"
OBJECT_PATH = "/"+BUS_NAME.replace(".", "/")
INTERFACE = BUS_NAME
    
# ---- Config ----
CONFIG_PATH = "/etc/tuxedo-power-profiles-adapter/config.toml"

# load_config reads the config file and returns a mapping of PowerProfiles profile names to tccd profile IDs.
def load_config():
    import toml

    print(f"Loading config from {CONFIG_PATH}...",flush=True)

    allowed_profiles = {"power-saver", "balanced", "performance"}
    defaults_profiles =  {"__legacy_powersave_extreme__", "__legacy_cool_and_breezy__", "__legacy_default__"}

    PROFILE_MAP = dict(zip(allowed_profiles, defaults_profiles))

    try:
        with open(CONFIG_PATH, "r") as f:
            config = toml.load(f)
    except FileNotFoundError:
        print(f"Warning: Config file {CONFIG_PATH} not found. Using default profile mapping.")
        return

    profile_map = config.get("profile_map")
    if not isinstance(profile_map, dict):
        print(f"Warning: Invalid or missing 'profile_map' in config. Using default profile mapping.")   
        return

    for name in allowed_profiles:
        tccd_id = profile_map.get(name)
        if isinstance(tccd_id, str) and tccd_id:
            PROFILE_MAP[name] = tccd_id

    unknown = set(profile_map.keys()) - allowed_profiles
    if unknown:
        print(f"Warning: Unknown profile_map keys ignored: {', '.join(sorted(unknown))}")

    return PROFILE_MAP

PROFILE_MAP = load_config()
REVERSE_MAP = {v: k for k, v in PROFILE_MAP.items()}


# TccdClient is responsible for communicating with tccd over D-Bus and providing 
# a simple API for getting the active profile and setting a new profile.
class TccdClient:

    def __init__(self, bus):
        self.bus = bus

    async def connect(self):

        introspection = await self.bus.introspect(TCCD_BUS, TCCD_PATH)

        obj = self.bus.get_proxy_object(
            TCCD_BUS,
            TCCD_PATH,
            introspection
        )

        self.iface = obj.get_interface(TCCD_INTERFACE)

    async def get_active(self):

        raw = await self.iface.call_get_active_profile_json()

        return json.loads(raw)

    async def set_profile(self, profile_id):

        await self.iface.call_set_temp_profile_by_id(profile_id)


# PowerProfiles adapter implementation. 
# This class implements the PowerProfiles D-Bus API and translates calls to the tccd client.
class PowerProfiles(ServiceInterface):

    def __init__(self, tccd):

        super().__init__(INTERFACE)

        self.tccd = tccd

        self._active = "balanced"

        self._profiles = [
            {"Profile": Variant("s", "power-saver")},
            {"Profile": Variant("s", "balanced")},
            {"Profile": Variant("s", "performance")}
        ]

    async def init_state(self):

        active = await self.tccd.get_active()

        tccd_id = active["id"]

        if tccd_id in REVERSE_MAP:
            self._active = REVERSE_MAP[tccd_id]

    @dbus_property(access=PropertyAccess.READ)
    def Profiles(self) -> "aa{sv}":

        return self._profiles

    @dbus_property(access=PropertyAccess.READWRITE)
    def ActiveProfile(self) -> "s":

        return self._active

    @ActiveProfile.setter
    def ActiveProfile(self, value: "s"):

        asyncio.create_task(self._switch_profile(value))

    async def _switch_profile(self, profile):

        if profile not in PROFILE_MAP:
            return

        tccd_id = PROFILE_MAP[profile]

        await self.tccd.set_profile(tccd_id)

        self._active = profile

        self.emit_properties_changed(
            {"ActiveProfile": self._active},
            []
        )

async def main():

    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    tccd = TccdClient(bus)

    await tccd.connect()

    service = PowerProfiles(tccd)

    await service.init_state()

    bus.export(OBJECT_PATH, service)

    await bus.request_name(BUS_NAME)

    print("tccd power profiles adapter running")

    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())