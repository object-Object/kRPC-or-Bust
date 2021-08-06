import krpc
import utils

# Connection setup
conn = krpc.connect()
vessel = conn.space_center.active_vessel

vessel.control.sas = False
vessel.control.rcs = False
vessel.auto_pilot.engage()

utils.hohmann(conn, vessel, 2863334)

vessel.control.sas = True