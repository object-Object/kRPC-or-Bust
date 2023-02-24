import math
import time

import krpc
import krpc.error
import settings


def _get_apoapsis_circularize_dv(orbit):
    mu = orbit.body.gravitational_parameter
    r = orbit.apoapsis
    a1 = orbit.semi_major_axis
    a2 = r
    v1 = math.sqrt(mu * ((2.0 / r) - (1.0 / a1)))
    v2 = math.sqrt(mu * ((2.0 / r) - (1.0 / a2)))
    return v2 - v1


def get_periapsis_circularize_dv(orbit):
    mu = orbit.body.gravitational_parameter
    r = orbit.periapsis
    a1 = orbit.semi_major_axis
    a2 = r
    v1 = math.sqrt(mu * ((2.0 / r) - (1.0 / a1)))
    v2 = math.sqrt(mu * ((2.0 / r) - (1.0 / a2)))
    return v1 - v2


def _get_hohmann_dv(orbit, target_altitude):
    mu = orbit.body.gravitational_parameter
    r1 = (orbit.apoapsis + orbit.periapsis) / 2
    r2 = target_altitude + orbit.body.equatorial_radius
    return math.sqrt(mu / r1) * (math.sqrt((2 * r2) / (r1 + r2)) - 1)


def _get_hohmann_transfer_time(orbit, target_altitude):
    mu = orbit.body.gravitational_parameter
    r1 = (orbit.apoapsis + orbit.periapsis) / 2
    r2 = target_altitude + orbit.body.equatorial_radius
    return math.pi * math.sqrt((r1 + r2) ** 3 / (8 * mu))


def _get_hohmann_transfer_angle(orbit, target_orbit):
    """Return value in radians."""
    r1 = (orbit.apoapsis + orbit.periapsis) / 2
    r2 = (target_orbit.apoapsis + target_orbit.periapsis) / 2
    return math.pi * (1 - math.sqrt((r1 / r2 + 1) ** 3) / (2 * math.sqrt(2)))


def _get_angle(object1, object2):
    ref_frame = object1.orbit.body.reference_frame
    angle = vec_angle(object1.position(ref_frame), object2.position(ref_frame))
    if vec_project(object1.velocity(ref_frame), object2.position(ref_frame)) < 0:
        angle = 2 * math.pi - angle
    return angle


def _get_time_to_angle(object1, object2, target_angle):
    angle = _get_angle(object1, object2)
    if angle == target_angle:
        return 0
    n1 = 2 * math.pi / object1.orbit.period
    n2 = 2 * math.pi / object2.orbit.period
    n = n2 - n1
    if angle < target_angle and n1 > n2:
        angle += 2 * math.pi
    elif angle > target_angle and n1 < n2:
        angle -= 2 * math.pi
    return (target_angle - angle) / n


def arrange_elements(elements, x_offset=0, y_offset=0):
    """Assumes all elements have the same height."""
    transforms = []
    for element in elements:
        transforms.append(element.rect_transform)
    center = transforms[0].position
    height = transforms[0].size[1]
    top = center[1] + (height + 2) * len(transforms) / 2
    for index, transform in enumerate(transforms):
        transform.position = (center[0] + x_offset, top - (height + 2) * index + y_offset)


def arrange_elements_with_labels(conn, elements, labels, x_offset=0, y_offset=0):
    x = max(e.rect_transform.size[0] for e in elements) / 2 + 4
    for label in labels:
        label.alignment = conn.ui.TextAnchor.middle_right
        label.rect_transform.pivot = (1, 0.5)
        label.rect_transform.position = (-x, label.rect_transform.position[1])
    arrange_elements(elements, x_offset=x_offset, y_offset=y_offset)
    arrange_elements(labels, x_offset=x_offset, y_offset=y_offset)


def get_burn_time(vessel, dv):
    F = vessel.available_thrust
    Isp = vessel.specific_impulse * 9.82
    m0 = vessel.mass
    m1 = m0 / math.exp(dv / Isp)
    flow_rate = F / Isp
    return (m0 - m1) / flow_rate


def get_dv_of_burn(vessel, burn_time):
    F = vessel.available_thrust
    v_e = vessel.specific_impulse * 9.82
    m0 = vessel.mass
    return -v_e * math.log(1 - (burn_time * F) / (m0 * v_e))


def get_braking_distance(vessel, speed):
    m0 = vessel.mass
    v_e = vessel.specific_impulse * 9.82
    F = vessel.available_thrust
    return 0.5 * speed * (m0 * (1 - math.exp(-speed / v_e)) * v_e) / F


def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))


def vec_magnitude(v):
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def vec_dot(v1, v2):
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]


def vec_angle(v1, v2):
    return math.acos(
        clamp(vec_dot(v1, v2) / (vec_magnitude(v1) * vec_magnitude(v2)), -1, 1)
    )  # clamp because of floating point errors


def vec_normalize(v):
    length = vec_magnitude(v)
    return (v[0] / length, v[1] / length, v[2] / length)


def vec_project(v, r):
    """Return the length of v projected onto r."""
    return vec_dot(vec_normalize(r), v)


def vec_sum(v1, v2):
    return (v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2])


def vec_difference(v1, v2):
    """v1 - v2"""
    return (v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2])


def vec_scalar_mult(k, v):
    return (k * v[0], k * v[1], k * v[2])


def log(conn, content, duration=5):
    print(content)
    conn.ui.message(content, duration=duration, position=conn.ui.MessagePosition.top_right)


def execute_node(conn, vessel, node, stop_condition=None):
    with conn.stream(getattr, node, "time_to") as time_to, conn.stream(
        getattr, node, "remaining_delta_v"
    ) as remaining_dv:
        log(conn, "Orienting for burn.")
        vessel.auto_pilot.reference_frame = node.reference_frame
        vessel.auto_pilot.target_direction = (0, 1, 0)
        vessel.auto_pilot.wait()

        log(conn, "Waiting to start burn.")
        burn_time = get_burn_time(vessel, remaining_dv())
        if time_to() > burn_time / 2 + 2:
            burn_ut = conn.space_center.ut + time_to() - burn_time / 2
            conn.space_center.warp_to(burn_ut - 2)

        while time_to() > burn_time / 2:
            time.sleep(settings.wait_sleep)

        log(conn, "Executing node.")
        if burn_time > 0.5:
            vessel.control.throttle = 1

        if stop_condition:
            stop_condition(burn_time)
        else:
            time.sleep(burn_time - 0.3)
            vessel.control.throttle = 0.05
            prev_dv = remaining_dv()
            while remaining_dv() - prev_dv <= 0:
                prev_dv = remaining_dv()
                time.sleep(0.01)  # intentionally not using settings.wait_sleep

        node.remove()
        vessel.control.throttle = 0


def circularize(conn, vessel):
    dv = _get_apoapsis_circularize_dv(vessel.orbit)
    node = vessel.control.add_node(
        conn.space_center.ut + vessel.orbit.time_to_apoapsis, prograde=dv
    )
    execute_node(conn, vessel, node)


def hohmann(conn, vessel, target_altitude):
    dv = _get_hohmann_dv(vessel.orbit, target_altitude)
    node = vessel.control.add_node(
        conn.space_center.ut + get_burn_time(vessel, dv) / 2 + 10, prograde=dv
    )
    log(conn, "Starting Hohmann transfer kick.")
    execute_node(conn, vessel, node)
    log(conn, "Starting Hohmann transfer circularization.")
    circularize(conn, vessel)


def hohmann_moon_rendezvous(
    conn, vessel, target, target_altitude, target_inclination=0, do_circularize=True
):
    """Vessel and target must be in circular coplanar orbits."""
    dv = _get_hohmann_dv(
        vessel.orbit, (target.orbit.apoapsis_altitude + target.orbit.periapsis_altitude) / 2
    )
    angle = _get_hohmann_transfer_angle(vessel.orbit, target.orbit)
    time_to_angle = _get_time_to_angle(vessel, target, angle)
    node = vessel.control.add_node(conn.space_center.ut + time_to_angle, prograde=dv)
    log(conn, "Starting Hohmann transfer kick.")

    def _rendezvous_stop_condition(burn_time):
        time.sleep(burn_time - 0.3)
        vessel.control.throttle = 0.05
        with conn.stream(vessel.orbit.distance_at_closest_approach, target.orbit) as approach_dist:
            prev_dist = approach_dist()
            while approach_dist() - prev_dist <= 0:
                prev_dist = approach_dist()
                time.sleep(0.01)  # intentionally not using settings.wait_sleep

    execute_node(conn, vessel, node, _rendezvous_stop_condition)

    next_orbit = vessel.orbit.next_orbit
    next_ref_frame = next_orbit.body.non_rotating_reference_frame
    if abs(next_orbit.periapsis_altitude - target_altitude) > 500:
        log(conn, "Orienting for altitude correction burn.")
        vessel.auto_pilot.reference_frame = next_ref_frame
        if next_orbit.periapsis_altitude > target_altitude:
            vessel.auto_pilot.target_direction = tuple(-x for x in vessel.position(next_ref_frame))
        else:
            vessel.auto_pilot.target_direction = vessel.position(next_ref_frame)
        vessel.auto_pilot.wait()
        log(conn, "Correcting altitude.")
        vessel.control.throttle = 0.01
        with conn.stream(getattr, next_orbit, "periapsis_altitude") as periapsis_altitude:
            if next_orbit.periapsis_altitude > target_altitude:
                while periapsis_altitude() > target_altitude:
                    time.sleep(settings.wait_sleep)
            else:
                while periapsis_altitude() < target_altitude:
                    time.sleep(settings.wait_sleep)
        vessel.control.throttle = 0

    if do_circularize:
        print("Waiting for SOI change.")
        # do stuff
        log(conn, "Starting Hohmann transfer circularization.")
        circularize(conn, vessel)


def warp_to_altitude(conn, vessel, altitude):
    true_anomaly = vessel.orbit.true_anomaly_at_radius(
        vessel.orbit.body.equatorial_radius + altitude
    )
    ut = min(
        vessel.orbit.ut_at_true_anomaly(true_anomaly),
        vessel.orbit.ut_at_true_anomaly(-true_anomaly),
    )
    conn.space_center.warp_to(ut)


def seconds_to_hms(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}"


def get_next_orbit_in_soi(orbit, body):
    time_to_orbit = 0
    while orbit is not None:
        try:
            if orbit.body == body:
                break
            time_to_orbit += (
                orbit.time_to_soi_change if not math.isnan(orbit.time_to_soi_change) else 0
            )
        except krpc.error.RPCError:
            pass
        orbit = orbit.next_orbit
    return (orbit, time_to_orbit)


def set_node_burn(node, burn_vector, delta_v):
    node.prograde = burn_vector[1]
    node.normal = burn_vector[2]
    node.radial = -burn_vector[0]
    node.delta_v = delta_v


def add_node_with_burn(control, ut, burn_vector, delta_v):
    """burn_vector should be in an orbital reference frame"""
    node = control.add_node(ut)
    set_node_burn(node, burn_vector, delta_v)
    return node
