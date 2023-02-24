# these types ONLY exist as stubs so this error isn't helpful
# pyright: reportMissingModuleSource = false

from typing import TYPE_CHECKING

from ._Stub import Stub

if TYPE_CHECKING:
    from krpc.spacecenter import SpaceCenter
else:
    SpaceCenter = Stub()

# Built-in types

Orbit = SpaceCenter.Orbit
CelestialBody = SpaceCenter.CelestialBody
Vessel = SpaceCenter.Vessel
Node = SpaceCenter.Node
Control = SpaceCenter.Control

# Additional helper types

HasOrbit = Vessel | CelestialBody
