import krpc
import utils

# Connection setup
conn = krpc.connect()
vessel = conn.space_center.active_vessel
target = conn.space_center.bodies["Mun"]

vessel.control.sas = False
vessel.control.rcs = False
vessel.auto_pilot.engage()

utils.hohmann_moon_rendezvous(conn, vessel, target, 2000000, do_circularize=False)

vessel.control.sas = True
