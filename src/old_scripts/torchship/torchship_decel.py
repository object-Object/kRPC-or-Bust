import sys

import krpc

from common import utils

if __name__ == "__main__":
    conn = krpc.connect()
    ut = conn.space_center.ut
    vessel = conn.space_center.active_vessel
    control = vessel.control
    target = conn.space_center.target_body

    if target is None:
        utils.log(conn, "Target must be a celestial body, aborting.")
        sys.exit()

    control.remove_nodes()

    (final_orbit, time_to_final_orbit) = utils.get_next_orbit_in_soi(vessel.orbit, target)
    if final_orbit is None:
        utils.log(conn, "Current orbit doesn't enter target's SOI, aborting.")
        sys.exit()
    time_to_periapsis = time_to_final_orbit + final_orbit.time_to_periapsis

    total_burn_dv = utils.get_periapsis_circularize_dv(final_orbit)
    total_burn_time = utils.get_burn_time(vessel, total_burn_dv)
    print(utils.seconds_to_hms(time_to_periapsis))
    time_to_burn_start = time_to_periapsis - total_burn_time / 2

    # num_nodes = 10
    # node_burn_time = total_burn_time / num_nodes
    # for i in range(1, num_nodes + 1):
    #     node = control.add_node(ut + time_to_burn_start + node_burn_time * i)
    #     hybrid_frame = conn.space_center.ReferenceFrame.create_hybrid(
    #         position=node.orbital_reference_frame,
    #         velocity=target.non_rotating_reference_frame
    #     )
    #     burn_vector = utils.vec_normalize(utils.vec_scalar_mult(-1, vessel.velocity(hybrid_frame)))
    #     utils.set_node_burn(node, burn_vector, utils.get_dv_of_burn(vessel, node_burn_time * i) - utils.get_dv_of_burn(vessel, node_burn_time * (i - 1)))

    node_burn_times = (
        [total_burn_time / 8] * 6 + [total_burn_time / 16] * 3 + [total_burn_time / 32] * 2
    )
    time_to_current_node = time_to_burn_start  # put the first node 1 minute + burn time away
    cumulative_velocity = vessel.velocity(target.non_rotating_reference_frame)
    cumulative_burn_time = 0
    for burn_time in node_burn_times:
        time_to_current_node += burn_time / 2
        node = control.add_node(ut + time_to_current_node)
        time_to_current_node += burn_time / 2
        # hybrid_frame = conn.space_center.ReferenceFrame.create_hybrid(
        #     position=vessel.orbital_reference_frame,
        #     rotation=node.orbital_reference_frame,
        #     velocity=target.orbit.body.non_rotating_reference_frame
        # )
        # burn_vector = utils.vec_normalize(utils.vec_difference(
        #     target.velocity(hybrid_frame),
        #     conn.space_center.transform_velocity(
        #         node.position(target.orbit.body.non_rotating_reference_frame),
        #         cumulative_velocity,
        #         target.orbit.body.non_rotating_reference_frame,
        #         hybrid_frame
        #     )
        # ))
        hybrid_frame = conn.space_center.ReferenceFrame.create_hybrid(
            position=node.orbital_reference_frame, velocity=target.non_rotating_reference_frame
        )
        burn_vector = utils.vec_normalize(
            utils.vec_scalar_mult(
                -1,
                conn.space_center.transform_velocity(
                    node.position(target.non_rotating_reference_frame),
                    cumulative_velocity,
                    target.non_rotating_reference_frame,
                    hybrid_frame,
                ),
            )
        )
        burn_dv = utils.get_dv_of_burn(
            vessel, burn_time + cumulative_burn_time
        ) - utils.get_dv_of_burn(vessel, cumulative_burn_time)
        utils.set_node_burn(node, burn_vector, burn_dv)
        cumulative_velocity = utils.vec_sum(
            cumulative_velocity, node.burn_vector(target.non_rotating_reference_frame)
        )
        cumulative_burn_time += burn_time

    utils.log(conn, "Nodes created. Use stability assist mode when nodes are nearly completed.")
    utils.log(conn, f"Estimated dv usage: {total_burn_dv}", 10)
    utils.log(conn, f"Estimated burn time: {utils.seconds_to_hms(total_burn_time)}", 10)
