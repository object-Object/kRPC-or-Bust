import re
import sys
import time

import krpc
import utils


def get_coast_time(distance, first_burn_dv, first_burn_time):
    return (distance - first_burn_dv * first_burn_time) / (first_burn_dv)


if __name__ == "__main__":
    # dv_budget = int(re.sub("\D", "", input("dv budget: ")))
    dv_budget = 100000

    conn = krpc.connect()
    vessel = conn.space_center.active_vessel
    control = vessel.control
    auto_pilot = vessel.auto_pilot
    target = conn.space_center.target_body

    if target is None:
        utils.log(conn, "Target must be a celestial body, aborting.")
        sys.exit()

    control.remove_nodes()

    # get an approximation of the target's position when we get there
    total_burn_dv = dv_budget / 2
    total_burn_time = utils.get_burn_time(vessel, total_burn_dv)

    burn_vector = utils.vec_normalize(
        target.orbit.position_at(conn.space_center.ut, vessel.orbital_reference_frame)
    )
    node = utils.add_node_with_burn(control, conn.space_center.ut, burn_vector, total_burn_dv)

    (final_orbit, _) = utils.get_next_orbit_in_soi(node.orbit, target.orbit.body)
    if final_orbit is None:
        utils.log(conn, "Failed to get naive arrival UT, aborting.")
        sys.exit()

    arrival_ut = final_orbit.time_of_closest_approach(target.orbit)
    node.remove()

    coast_speed = utils.vec_magnitude(
        utils.vec_sum(
            utils.vec_scalar_mult(
                total_burn_dv,
                utils.vec_normalize(
                    utils.vec_difference(
                        target.orbit.position_at(
                            arrival_ut, target.orbit.body.non_rotating_reference_frame
                        ),
                        vessel.position(target.orbit.body.non_rotating_reference_frame),
                    )
                ),
            ),
            vessel.velocity(target.orbit.body.non_rotating_reference_frame),
        )
    )

    control.sas = False
    auto_pilot.engage()
    auto_pilot.reference_frame = vessel.orbital_reference_frame
    auto_pilot.target_direction = target.position(vessel.orbital_reference_frame)
    auto_pilot.wait()
    auto_pilot.disengage()

    node = control.add_node(conn.space_center.ut + 3)
    utils.set_node_burn(
        node, utils.vec_normalize(vessel.direction(node.orbital_reference_frame)), total_burn_dv
    )
    control.sas = True
    time.sleep(0.2)
    auto_pilot.sas_mode = conn.space_center.SASMode.maneuver
    control.throttle = 1

    remaining_burn_dv = total_burn_dv
    while remaining_burn_dv / total_burn_dv > 0.2:
        hybrid_frame = conn.space_center.ReferenceFrame.create_hybrid(
            position=vessel.orbital_reference_frame,
            rotation=node.orbital_reference_frame,
            velocity=target.orbit.body.non_rotating_reference_frame,
        )
        burn_vector = utils.vec_difference(
            utils.vec_scalar_mult(
                coast_speed,
                utils.vec_normalize(
                    utils.vec_difference(
                        target.orbit.position_at(arrival_ut, hybrid_frame),
                        vessel.position(hybrid_frame),
                    )
                ),
            ),
            vessel.velocity(hybrid_frame),
        )
        remaining_burn_dv = utils.vec_magnitude(burn_vector)
        old_node = node
        node = control.add_node(
            conn.space_center.ut + 3 * conn.space_center.warp_rate,
            burn_vector[1],
            burn_vector[2],
            -burn_vector[0],
        )
        old_node.remove()

    while remaining_burn_dv > 100:
        (final_orbit, _) = utils.get_next_orbit_in_soi(vessel.orbit, target)
        if final_orbit is None:
            (final_orbit, _) = utils.get_next_orbit_in_soi(vessel.orbit, target.orbit.body)
        arrival_ut = final_orbit.time_of_closest_approach(target.orbit)
        hybrid_frame = conn.space_center.ReferenceFrame.create_hybrid(
            position=vessel.orbital_reference_frame,
            rotation=node.orbital_reference_frame,
            velocity=target.orbit.body.non_rotating_reference_frame,
        )
        burn_vector = utils.vec_normalize(
            utils.vec_difference(
                target.orbit.position_at(arrival_ut, hybrid_frame),
                final_orbit.position_at(arrival_ut, hybrid_frame),
            )
        )
        if utils.vec_magnitude(burn_vector) < target.equatorial_radius:
            burn_vector = utils.vec_normalize(vessel.velocity(hybrid_frame))
        remaining_burn_dv = coast_speed - utils.vec_magnitude(
            vessel.velocity(target.non_rotating_reference_frame)
        )
        burn_vector = utils.vec_scalar_mult(remaining_burn_dv, burn_vector)
        old_node = node
        node = control.add_node(
            conn.space_center.ut + 3 * conn.space_center.warp_rate,
            burn_vector[1],
            burn_vector[2],
            -burn_vector[0],
        )
        old_node.remove()
    print(remaining_burn_dv)
    control.throttle = 0
    control.remove_nodes()
