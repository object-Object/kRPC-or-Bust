import krpc, utils, time

def get_current_acceleration(vessel):
    return vessel.thrust / vessel.mass

desired_acceleration = 9.81
allowed_error = 0.001

if __name__ == '__main__':
    conn = krpc.connect()
    Expression = conn.krpc.Expression
    vessel = conn.space_center.active_vessel
    control = vessel.control

    with conn.stream(getattr, vessel, "thrust") as thrust, conn.stream(getattr, vessel, "mass") as mass, conn.stream(getattr, control, "throttle") as throttle:
        while True:
            if throttle() > 0 and abs(thrust() / mass() - desired_acceleration) > allowed_error:
                # control.throttle = 1
                # for engine in vessel.parts.engines: # because kspi doesn't play nice with krpc
                #     engine.thrust_limit = 1
                thrust_limit = desired_acceleration / (vessel.max_thrust / vessel.mass)
                if thrust_limit > 1:
                    utils.log(conn, "Warning: desired acceleration is currently impossible.")
                    thrust_limit = 1
                # for engine in vessel.parts.engines:
                #     engine.thrust_limit = thrust_limit
                control.throttle = thrust_limit
            time.sleep(0.1)