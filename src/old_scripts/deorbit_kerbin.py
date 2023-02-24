# Assumes the active stage has an engine and the next stage has a parachute and optional decoupler
import time

import krpc

from common import settings, utils

# Connection setup
conn = krpc.connect()
vessel = conn.space_center.active_vessel

# Telemetry
periapsis = conn.add_stream(getattr, vessel.orbit, "periapsis_altitude")
liquid_fuel = conn.add_stream(vessel.resources.amount, "LiquidFuel")
altitude = conn.add_stream(getattr, vessel.flight(), "mean_altitude")
speed = conn.add_stream(getattr, vessel.flight(vessel.orbit.body.reference_frame), "speed")

vessel.control.sas = False
vessel.control.rcs = False

utils.log(conn, "Waiting until apoapsis.")
conn.space_center.warp_to(conn.space_center.ut + vessel.orbit.time_to_apoapsis)

utils.log(conn, "Orienting retrograde.")
vessel.auto_pilot.engage()
vessel.auto_pilot.reference_frame = vessel.orbital_reference_frame
vessel.auto_pilot.target_direction = (0, -1, 0)
vessel.auto_pilot.wait()
vessel.auto_pilot.wait()

utils.log(conn, "Deorbiting.")
vessel.control.throttle = 1
while periapsis() > 30000:
    time.sleep(settings.wait_sleep)
vessel.control.throttle = 0
time.sleep(0.5)
vessel.control.activate_next_stage()

utils.log(conn, "Waiting for atmosphere.")
utils.warp_to_altitude(conn, vessel, 70100)

utils.log(conn, "Tracking retrograde.")
vessel.auto_pilot.reference_frame = vessel.orbital_reference_frame
vessel.auto_pilot.target_direction = (0, -1, 0)

if vessel.available_thrust > 0:
    while altitude() > 35000:
        time.sleep(settings.wait_sleep)
    utils.log(conn, "Decelerating.")
    vessel.control.throttle = 1

while altitude() > 10000 and speed() > 1000:
    time.sleep(settings.wait_sleep)

vessel.control.throttle = 0
