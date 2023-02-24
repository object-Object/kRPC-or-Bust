# Assumes the active stage has an engine
import time

import krpc
import settings
import utils

# Connection setup
conn = krpc.connect()
vessel = conn.space_center.active_vessel
space_high = vessel.orbit.body.space_high_altitude_threshold

# Telemetry
apoapsis = conn.add_stream(getattr, vessel.orbit, "apoapsis_altitude")
altitude = conn.add_stream(getattr, vessel.flight(), "mean_altitude")

vessel.control.sas = False
vessel.control.rcs = False

utils.log(conn, "Orienting prograde.")
vessel.auto_pilot.engage()
vessel.auto_pilot.reference_frame = vessel.orbital_reference_frame
vessel.auto_pilot.target_direction = (0, 1, 0)
vessel.auto_pilot.wait()

utils.log(conn, "Raising apoapsis.")
vessel.control.throttle = 1
while apoapsis() < space_high + 2000:
    time.sleep(settings.wait_sleep)
vessel.control.throttle = 0
vessel.auto_pilot.disengage()
vessel.control.sas = True

utils.log(conn, "Waiting to gain altitude.")
time.sleep(settings.warp_sleep)
utils.warp_to_altitude(conn, vessel, space_high)

for experiment in vessel.parts.experiments:
    utils.log(conn, f"Running {experiment.part.title}.")
    experiment.run()

time.sleep(2)
vessel.parts.modules_with_name("ModuleScienceContainer")[0].set_action("Collect All")
