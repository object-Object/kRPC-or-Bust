import krpc, utils, sys

def get_coast_time(distance, first_burn_dv, first_burn_time):
    return (distance - first_burn_dv*first_burn_time) / (first_burn_dv)

if __name__ == '__main__':
    dv_budget = int(input("dv budget: "))
    #dv_budget = 100000

    conn = krpc.connect()
    ut = conn.space_center.ut
    vessel = conn.space_center.active_vessel
    control = vessel.control
    target = conn.space_center.target_body

    if target is None:
        utils.log(conn, "Target must be a celestial body, aborting.")
        sys.exit()

    control.remove_nodes()

    # get an approximation of the target's position when we get there
    total_burn_dv = dv_budget / 2
    total_burn_time = utils.get_burn_time(vessel, total_burn_dv)

    burn_vector = utils.vec_normalize(target.orbit.position_at(ut, vessel.orbital_reference_frame))
    node = utils.add_node_with_burn(control, ut, burn_vector, total_burn_dv)

    (final_orbit, _) = utils.get_next_orbit_in_soi(node.orbit, target.orbit.body)
    if final_orbit is None:
        utils.log(conn, "Failed to get naive arrival UT, aborting.")
        sys.exit()
    
    naive_arrival_ut = final_orbit.time_of_closest_approach(target.orbit)
    node.remove()
    
    # create nodes to approximate a long burn
    node_burn_times = [total_burn_time/32]*2 + [total_burn_time/16]*3 + [total_burn_time/8]*6
    time_to_current_node = 60 # put the first node 1 minute + burn time away
    cumulative_velocity = vessel.velocity(target.orbit.body.non_rotating_reference_frame)
    cumulative_burn_time = 0
    for burn_time in node_burn_times:
        time_to_current_node += burn_time
        node = control.add_node(ut + time_to_current_node)
        hybrid_frame = conn.space_center.ReferenceFrame.create_hybrid(
            position=vessel.orbital_reference_frame,
            rotation=node.orbital_reference_frame,
            velocity=target.orbit.body.non_rotating_reference_frame
        )
        burn_vector = utils.vec_normalize(utils.vec_difference(
            utils.vec_scalar_mult(total_burn_dv, utils.vec_normalize(target.orbit.position_at(naive_arrival_ut, hybrid_frame))),
            conn.space_center.transform_velocity(
                node.position(target.orbit.body.non_rotating_reference_frame),
                cumulative_velocity,
                target.orbit.body.non_rotating_reference_frame,
                hybrid_frame
            )
        ))
        burn_dv = utils.get_dv_of_burn(vessel, burn_time + cumulative_burn_time) - utils.get_dv_of_burn(vessel, cumulative_burn_time)
        utils.set_node_burn(node, burn_vector, burn_dv)
        cumulative_velocity = utils.vec_sum(cumulative_velocity, node.burn_vector(target.orbit.body.non_rotating_reference_frame))
        cumulative_burn_time += burn_time

    coast_time = get_coast_time(utils.vec_magnitude(target.orbit.position_at(naive_arrival_ut, vessel.orbital_reference_frame)), total_burn_dv, total_burn_time)
    utils.log(conn, "Nodes created. Use stability assist mode when nodes are nearly completed.")
    utils.log(conn, f"Estimated dV usage: {dv_budget:,}m/s", 10)
    utils.log(conn, f"Estimated departure burn time: {utils.seconds_to_hms(total_burn_time)}", 10)
    utils.log(conn, f"Estimated coast time: {utils.seconds_to_hms(coast_time)}", 10)
    utils.log(conn, f"Estimated total travel time: {utils.seconds_to_hms(coast_time + 2*total_burn_time)}", 10)