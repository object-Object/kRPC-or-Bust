import krpc
import time
from krpc.platform import NAN
import utils
import math
import settings

# turn_start_speed, turn_start_pitch, target_apoapsis, apoapsis_margin, num_srb_boosters, has_fairing, has_payload
ships = {
	"KPR Tom's Hairball": (20, 2.9, 90000, 100, 1, False, False), # TWR: 1.80
	"LLV Longcat's Night": (20, 4.6, 80000, -100, 1, True, True),
}

# Constants
target_inclination = 0
exact_inclination = False
max_physics_warp = 2 # 0-3

# Connection setup
conn = krpc.connect()
vessel = conn.space_center.active_vessel
(turn_start_speed, turn_start_pitch, target_apoapsis, apoapsis_margin, num_srb_boosters, has_fairing, has_payload) = ships[vessel.name]
prograde_ref = conn.space_center.ReferenceFrame.create_hybrid(position=vessel.orbit.body.reference_frame, rotation=vessel.surface_reference_frame)
target_heading = 90 - target_inclination
target_heading -= 3*math.cos(math.radians(target_heading)) # help compensate for rotation for non-equatorial orbits

# Wait for start button to be pressed (KSP acts different depending on window focus status)
button = conn.ui.stock_canvas.add_button("Launch")
with conn.stream(getattr, button, "clicked") as clicked:
	while not clicked():
		time.sleep(settings.wait_sleep)
button.remove()

# Telemetry streams
altitude = conn.add_stream(getattr, vessel.flight(), "mean_altitude")
apoapsis = conn.add_stream(getattr, vessel.orbit, "apoapsis_altitude")
periapsis = conn.add_stream(getattr, vessel.orbit, "periapsis_altitude")
srf_speed = conn.add_stream(getattr, vessel.flight(vessel.orbit.body.reference_frame), "speed")
prograde = conn.add_stream(getattr, vessel.flight(prograde_ref), "velocity")
if num_srb_boosters > 0:
	srb_fuel = [conn.add_stream(vessel.resources_in_decouple_stage(vessel.control.current_stage-x).amount, "SolidFuel") for x in range(2, 2+num_srb_boosters)]

# Prelaunch setup
vessel.control.sas = False
vessel.control.rcs = False
vessel.control.throttle = 1
srb_low_fuel_qty = [x() * 0.05 for x in srb_fuel]

# Countdown
utils.log(conn, "T-3...")
time.sleep(1)
utils.log(conn, "T-2...")
time.sleep(1)
utils.log(conn, "T-1...")
time.sleep(1)

utils.log(conn, "Launching.")
vessel.control.activate_next_stage()
vessel.auto_pilot.engage()
vessel.auto_pilot.reference_frame = vessel.surface_reference_frame
vessel.auto_pilot.target_roll = NAN
vessel.auto_pilot.target_pitch_and_heading(90, target_heading)

utils.log(conn, "Waiting until turn start speed.")
while srf_speed() < turn_start_speed:
	time.sleep(settings.wait_sleep)

utils.log(conn, "Starting gravity turn.")
vessel.auto_pilot.target_pitch = 90-turn_start_pitch
vessel.auto_pilot.wait()
target_heading_x = math.sin(math.radians(90-turn_start_pitch)) # wait for prograde pitch to equal turn_start_pitch
while utils.normalize(prograde())[0] > target_heading_x:
	time.sleep(settings.wait_sleep)

utils.log(conn, "Tracking prograde.")
conn.space_center.physics_warp_factor = max_physics_warp
warping = True
num_srb_BECO = 0
while apoapsis() < target_apoapsis+apoapsis_margin:
	vessel.auto_pilot.target_pitch = math.degrees(math.asin(utils.normalize(prograde())[0]))
	if num_srb_BECO < num_srb_boosters:
		if warping and srb_fuel[num_srb_BECO]() <= srb_low_fuel_qty[num_srb_BECO]:
			conn.space_center.physics_warp_factor = 0
			warping = False
		if srb_fuel[num_srb_BECO]() == 0:
			num_srb_BECO += 1
			utils.log(conn, f"BECO{' '+num_srb_BECO if num_srb_BECO < num_srb_BECO else ''}.")
			vessel.control.activate_next_stage()
			time.sleep(settings.warp_sleep)
			conn.space_center.physics_warp_factor = max_physics_warp
			warping = True
	if warping and apoapsis() >= target_apoapsis+apoapsis_margin-10000:
		conn.space_center.physics_warp_factor = 0
		warping = False
	time.sleep(settings.wait_sleep)

utils.log(conn, "MECO 1. Coasting out of atmosphere.")
vessel.auto_pilot.reference_frame = vessel.surface_velocity_reference_frame
vessel.auto_pilot.target_direction = (0, 1, 0)
vessel.control.throttle = 0
time.sleep(settings.warp_sleep)
conn.space_center.physics_warp_factor = max_physics_warp
warping = True
while altitude() < 70100:
	if warping and altitude() >= 69000:
		conn.space_center.physics_warp_factor = 0
		warping = False
	time.sleep(settings.wait_sleep)

if has_fairing:
	utils.log(conn, "Separating fairing.")
	vessel.control.activate_next_stage()
	time.sleep(0.5)

utils.circularize(conn, vessel)

if not has_payload:
	vessel.control.sas = True
else:
	utils.log(conn, "Waiting to stabilize.")
	vessel.auto_pilot.disengage()
	vessel.control.sas = True
	time.sleep(4)

	utils.log(conn, "Separating booster.")
	booster = vessel.control.activate_next_stage()[0]
	time.sleep(3)

	utils.log(conn, "Deorbiting booster.")
	booster.control.sas = False
	booster.auto_pilot.engage()
	booster.auto_pilot.reference_frame = booster.orbital_reference_frame
	booster.auto_pilot.target_direction = (0, -1, 0)
	booster.auto_pilot.wait()
	booster.auto_pilot.wait()
	booster.control.throttle = 1
	booster.control.sas = True
