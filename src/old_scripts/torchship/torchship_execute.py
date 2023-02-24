import time

import krpc
import utils


def wait_for_dv(conn, node, fraction):
    total_dv = node.delta_v
    with conn.stream(getattr, node, "remaining_delta_v") as remaining_dv:
        with remaining_dv.condition:
            while remaining_dv() / total_dv > fraction:
                remaining_dv.wait()


if __name__ == "__main__":
    conn = krpc.connect()
    vessel = conn.space_center.active_vessel
    control = vessel.control
    auto_pilot = vessel.auto_pilot

    utils.log(conn, "Aligning to burn vector.")
    control.sas = True
    auto_pilot.sas_mode = conn.space_center.SASMode.maneuver
    time.sleep(5)

    utils.log(conn, "Warping to start of burn.")
    conn.space_center.warp_to(
        control.nodes[0].ut - utils.get_burn_time(vessel, control.nodes[0].delta_v) / 2 - 3
    )
    time.sleep(3)

    utils.log(conn, "Starting burn. You can enable thrust warp now.")
    control.throttle = 1

    while len(control.nodes) > 1:
        wait_for_dv(conn, control.nodes[0], 0.05)
        control.nodes[0].remove()

    wait_for_dv(conn, control.nodes[0], 0.5)

    control.throttle = 0
    conn.space_center.rails_warp_factor = 0
    utils.log(conn, "Disengaging.")
