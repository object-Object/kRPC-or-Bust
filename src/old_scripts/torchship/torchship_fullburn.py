import math
import sys
import time

import krpc

from common import utils


def wait_for_flip(conn, vessel, target, target_is_body, lead_time, message):
    screen_size = conn.ui.stock_canvas.rect_transform.size

    text = conn.ui.stock_canvas.add_text(f"{message}:")
    text.rect_transform.position = (0, (screen_size[1] / 2) - 160)
    text.rect_transform.size = (800, 50)
    text.color = (1, 1, 1)
    text.size = 18
    text.alignment = conn.ui.TextAnchor.middle_center

    while True:
        speed = utils.vec_magnitude(vessel.velocity(target.orbital_reference_frame))
        orbit = None
        if target_is_body:
            (orbit, time_to_soi) = utils.get_next_orbit_in_soi(vessel.orbit, target)
        if orbit is not None:  # straight line distance to periapsis
            current_distance = utils.vec_magnitude(
                utils.vec_difference(
                    vessel.position(target.orbital_reference_frame),
                    orbit.position_at(
                        conn.space_center.ut + time_to_soi + orbit.time_to_periapsis,
                        target.orbital_reference_frame,
                    ),
                )
            )
        else:  # straight line distance to center of target
            current_distance = utils.vec_magnitude(vessel.position(target.orbital_reference_frame))
        distance_until_flip = (
            current_distance - utils.get_braking_distance(vessel, speed) - speed * lead_time
        )
        if distance_until_flip <= 0:
            text.remove()
            return
        text.content = f"{message}: {int(distance_until_flip):,} m"
        time.sleep(0.1)


if __name__ == "__main__":
    flip_margin = 200  # will flip and burn this many seconds early

    conn = krpc.connect()
    vessel = conn.space_center.active_vessel
    control = vessel.control
    auto_pilot = vessel.auto_pilot
    (target, target_is_body) = (
        (conn.space_center.target_body, True)
        if conn.space_center.target_body
        else (conn.space_center.target_vessel, False)
    )

    if target is None:
        utils.log(conn, "Target must be a celestial body or vessel, aborting.")
        sys.exit()

    D = utils.vec_magnitude(target.position(vessel.orbital_reference_frame))
    A = vessel.available_thrust / vessel.mass
    utils.log(conn, f"Estimated dv usage: {int(2 * math.sqrt(D * A)):,}m/s", 10)
    utils.log(conn, f"Estimated travel time: {utils.seconds_to_hms(2 * math.sqrt(D / A))}", 10)

    utils.log(conn, "Pointing at target.")
    control.throttle = 0
    control.sas = False

    auto_pilot.engage()
    auto_pilot.reference_frame = vessel.orbital_reference_frame
    auto_pilot.target_direction = target.position(vessel.orbital_reference_frame)
    auto_pilot.target_roll = math.nan
    auto_pilot.wait()
    auto_pilot.disengage()

    utils.log(conn, "Starting acceleration burn.")
    control.sas = True
    time.sleep(0.5)
    auto_pilot.sas_mode = conn.space_center.SASMode.target
    control.throttle = 1
    time.sleep(1)  # things are buggy right at the start of the burn, so just skip that
    wait_for_flip(conn, vessel, target, target_is_body, flip_margin + 60, "Distance until flip")

    utils.log(conn, "Flipping and waiting to start deceleration burn.")
    conn.space_center.rails_warp_factor = 0
    control.throttle = 0
    if not target_is_body or vessel.orbit.body != target:
        control.speed_mode = conn.space_center.SpeedMode.target
        time.sleep(0.5)
    auto_pilot.sas_mode = conn.space_center.SASMode.retrograde
    wait_for_flip(conn, vessel, target, target_is_body, flip_margin, "Distance until burn")

    utils.log(conn, "Starting deceleration burn.")
    conn.space_center.rails_warp_factor = 0
    control.throttle = 1

    utils.log(conn, "Disengaging.")
