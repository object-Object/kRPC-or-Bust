# kRPC-or-Bust
Flight control software for rockets and torchships in KSP.

## About this repo

The goal of this repo was to see how far I could get in Kerbal Space Program with a fully autonomous rocket — no manual controls at all. I later added some scripts to help control torchships.

Please keep in mind that some of these scripts are very old, and I've learned a lot about software best practices and proper Python formatting since then.

## Files

### Autonomous rocket control

* [sounding.py](sounding.py): Simple sounding rocket that waits until apoapsis, then deploys a parachute.
* [gravturn.py](gravturn.py) and [gravturn_worker.py](gravturn_worker.py): Autonomous gravity turn execution, from launchpad to orbit.
* [mun_science.py](mun_science.py) and [high_space_science.py](high_space_science.py): Scripts to modify a capsule's orbit and collect science from different altitudes.
* [hohmann.py](hohmann.py): Helper script to execute an automatic Hohmann transfer, moving a rocket to a higher or lower orbit.
* [utils.py](utils.py): Many utility functions used in the above scripts.

### Torchships

All files starting with `torchship`, as well as [constant_acceleration.py](constant_acceleration.py), are various attempts at making a functional control program for a torchship to follow a brachistochrone trajectory (basically point at the target and hit go, with a flip-and-burn maneuver somewhere in the middle like in the Expanse). I believe [torchship_fullburn.py](torchship_fullburn.py) and [torchship_readout.py](torchship_readout.py) are the versions that work the best.
