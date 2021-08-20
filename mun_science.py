import krpc
import time
import utils
import settings

# Connection setup
conn = krpc.connect()
vessel = conn.space_center.active_vessel

vessel.control.sas = True
vessel.control.rcs = False

utils.log(conn, "Waiting for Munar periapsis.")
conn.space_center.warp_to(conn.space_center.ut+vessel.orbit.next_orbit.time_to_periapsis)

for experiment in vessel.parts.experiments:
	utils.log(conn, f"Running {experiment.part.title}.")
	experiment.run()

time.sleep(2)
utils.log(conn, "Collecting science.")
vessel.parts.modules_with_name("ModuleScienceContainer")[0].set_action("Collect All")

utils.log(conn, "Waiting to leave Mun SOI.")
conn.space_center.warp_to(conn.space_center.ut+vessel.orbit.time_to_soi_change+10)