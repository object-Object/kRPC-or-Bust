import krpc, utils, sys, time, math

if __name__ == '__main__':
    flip_margin = 200 # s

    conn = krpc.connect()
    vessel = conn.space_center.active_vessel
    control = vessel.control
    auto_pilot = vessel.auto_pilot

    screen_size = conn.ui.stock_canvas.rect_transform.size

    text = conn.ui.stock_canvas.add_text(f"Distance to flip/burn:")
    text.rect_transform.position = (0, (screen_size[1]/2)-160)
    text.rect_transform.size = (800, 50)
    text.color = (1, 1, 1)
    text.size = 18
    text.alignment = conn.ui.TextAnchor.middle_center

    while True:
        (target, target_is_body) = (conn.space_center.target_body, True) if conn.space_center.target_body else (conn.space_center.target_vessel, False)

        if target:
            speed = utils.vec_magnitude(vessel.velocity(target.orbital_reference_frame))
            orbit = None
            if target_is_body:
                (orbit, time_to_soi) = utils.get_next_orbit_in_soi(vessel.orbit, target)
            if orbit is not None: # straight line distance to periapsis
                current_distance = utils.vec_magnitude(utils.vec_difference(
                    vessel.position(target.orbital_reference_frame),
                    orbit.position_at(conn.space_center.ut + time_to_soi + orbit.time_to_periapsis, target.orbital_reference_frame)
                ))
            else: # straight line distance to center of target
                current_distance = utils.vec_magnitude(vessel.position(target.orbital_reference_frame))
            distance_until_flip = current_distance - utils.get_braking_distance(vessel, speed) - speed*flip_margin
            text.content = f"Distance to flip/burn: {int(distance_until_flip):,} m"
        else:
            text.content = "No target set."
        time.sleep(0.1)
