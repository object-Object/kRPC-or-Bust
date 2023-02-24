Many kRPC types can't be directly imported. For example, the Vessel type is only accessible like so:
```py
from krpc.spacecenter import SpaceCenter

vessel: SpaceCenter.Vessel = ...
```
The files in this directory exist only to re-export those types for better ergonomics (and also to hide the false-positive `reportMissingModuleSource` errors that show up from importing these classes).
