import krpc
import time
import utils
import math

def worker(queue):
	conn = krpc.connect()
	vessel = conn.space_center.active_vessel
	direction = conn.add_stream(vessel.direction, vessel.surface_reference_frame)
	altitude = conn.add_stream(getattr, vessel.flight(), "mean_altitude")
	physics_warp_factor = conn.add_stream(getattr, conn.space_center, "physics_warp_factor")

	direction_data = []
	other_data = []
	started_physics_warp = False

	while True:
		if queue.empty():
			current_direction = direction()
			current_altitude = altitude()
			if not direction_data or utils.vec_angle(current_direction, direction_data[-1][1])>0.00175:
				direction_data.append((current_altitude, current_direction))
			if not started_physics_warp and physics_warp_factor() > 0:
				other_data.append((current_altitude, "start_physics_warp", 2))
				started_physics_warp = True
			time.sleep(0.0001)
		else:
			item = queue.get()
			if item=="END":
				queue.put({"direction_data": direction_data, "other_data": other_data})
				queue.task_done()
				queue.task_done()
				conn.close()
				return
