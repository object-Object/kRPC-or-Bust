import math
import time
import settings

def _get_apoapsis_circularize_dv(orbit):
	mu = orbit.body.gravitational_parameter
	r = orbit.apoapsis
	a1 = orbit.semi_major_axis
	a2 = r
	v1 = math.sqrt(mu*((2./r)-(1./a1)))
	v2 = math.sqrt(mu*((2./r)-(1./a2)))
	return v2 - v1

def _get_hohmann_dv(orbit, target_altitude):
	mu = orbit.body.gravitational_parameter
	r1 = (orbit.apoapsis+orbit.periapsis)/2
	r2 = target_altitude+orbit.body.equatorial_radius
	return math.sqrt(mu/r1)*(math.sqrt((2*r2)/(r1+r2))-1)

def _get_hohmann_transfer_time(orbit, target_altitude):
	mu = orbit.body.gravitational_parameter
	r1 = (orbit.apoapsis+orbit.periapsis)/2
	r2 = target_altitude+orbit.body.equatorial_radius
	return math.pi*math.sqrt((r1+r2)**3/(8*mu))

def _get_hohmann_transfer_angle(orbit, target_altitude): # returns value in radians
	r1 = (orbit.apoapsis+orbit.periapsis)/2
	r2 = target_altitude+orbit.body.equatorial_radius
	return math.pi*(1-math.sqrt((r1/r2+1)**3)/(2*math.sqrt(2)))

def get_burn_time(vessel, dv):
	F = vessel.available_thrust
	Isp = vessel.specific_impulse * 9.82
	m0 = vessel.mass
	m1 = m0 / math.exp(dv/Isp)
	flow_rate = F / Isp
	return (m0 - m1) / flow_rate

def normalize(v):
	length = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
	return (v[0]/length, v[1]/length, v[2]/length)

def log(conn, content):
	print(content)
	conn.ui.message(content, duration=4, position=conn.ui.MessagePosition.top_right)

def execute_node(conn, vessel, node, stop_condition=None):
	with conn.stream(getattr, node, "time_to") as time_to, conn.stream(getattr, node, "remaining_delta_v") as remaining_dv:
		log(conn, "Orienting for burn.")
		vessel.auto_pilot.reference_frame = node.reference_frame
		vessel.auto_pilot.target_direction = (0, 1, 0)
		vessel.auto_pilot.wait()

		log(conn, "Waiting to start burn.")
		burn_time = get_burn_time(vessel, remaining_dv())
		if time_to() > burn_time/2+2:
			burn_ut = conn.space_center.ut + time_to() - burn_time/2
			conn.space_center.warp_to(burn_ut-2)

		while time_to() > burn_time/2:
			time.sleep(settings.wait_sleep)

		log(conn, "Executing node.")
		if burn_time > 0.5:
			vessel.control.throttle = 1

		if stop_condition:
			stop_condition()
		else:
			time.sleep(burn_time-0.3)
			vessel.control.throttle = 0.05
			prev_dv = remaining_dv()
			while remaining_dv()-prev_dv <= 0:
				prev_dv = remaining_dv()
				time.sleep(0.01) # intentionally not using settings.wait_sleep

		node.remove()
		vessel.control.throttle = 0

def circularize(conn, vessel):
	dv = _get_apoapsis_circularize_dv(vessel.orbit)
	node = vessel.control.add_node(conn.space_center.ut+vessel.orbit.time_to_apoapsis, prograde=dv)
	execute_node(conn, vessel, node)

def hohmann(conn, vessel, target_altitude):
	dv = _get_hohmann_dv(vessel.orbit, target_altitude)
	node = vessel.control.add_node(conn.space_center.ut+get_burn_time(vessel, dv)/2+10, prograde=dv)
	log(conn, "Starting Hohmann transfer kick.")
	execute_node(conn, vessel, node)
	log(conn, "Starting Hohmann transfer circularization.")
	circularize(conn, vessel)

def warp_to_altitude(conn, vessel, altitude):
	true_anomaly = vessel.orbit.true_anomaly_at_radius(vessel.orbit.body.equatorial_radius+altitude)
	ut = min(vessel.orbit.ut_at_true_anomaly(true_anomaly), vessel.orbit.ut_at_true_anomaly(-true_anomaly))
	conn.space_center.warp_to(ut)
