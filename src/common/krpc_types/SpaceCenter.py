# these types ONLY exist as stubs until runtime so this error isn't helpful
# pyright: reportMissingModuleSource = false

from krpc.spacecenter import SpaceCenter

# Built-in types

Orbit = SpaceCenter.Orbit
CelestialBody = SpaceCenter.CelestialBody
Vessel = SpaceCenter.Vessel
Node = SpaceCenter.Node
Control = SpaceCenter.Control

# Additional helper types

HasOrbit = Vessel | CelestialBody
