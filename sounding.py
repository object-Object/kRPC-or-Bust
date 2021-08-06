import krpc
import time

conn = krpc.connect()
vessel = conn.space_center.active_vessel
srf_flight = vessel.flight(vessel.orbit.body.reference_frame)
experiments = vessel.parts.experiments.copy()

# Telemetry
altitude = conn.add_stream(getattr, srf_flight, "mean_altitude")
speed = conn.add_stream(getattr, vessel.flight(vessel.orbit.body.reference_frame), "speed")

vessel.control.activate_next_stage()
vessel.auto_pilot.engage()
vessel.auto_pilot.target_pitch_and_heading(89, 90)
print("Launched.")
# print("Waiting to gain altitude...")
# while altitude() < 300:
# 	time.sleep(0.1)

# vessel.auto_pilot.reference_frame = vessel.surface_velocity_reference_frame
# vessel.auto_pilot.target_direction = (0, 1, 0)

print("Waiting to gain altitude...")
while altitude() < 3100 or speed() > 90:
	time.sleep(0.1)

# run_experiments = []
# for experiment in experiments:
# 	if not experiment.name in run_experiments:
# 		print(f"Running {experiment.part.title}.")
# 		experiment.run()
# 		#experiment.transmit()
# 		run_experiments.append(experiment.name)
# 		experiments.remove(experiment)

# print("Waiting to gain altitude...")
# while altitude() < 18500:
# 	time.sleep(0.1)

# run_experiments = []
# for experiment in experiments:
# 	if not experiment.name in run_experiments:
# 		print(f"Running {experiment.part.title}.")
# 		experiment.run()
# 		#experiment.transmit()
# 		run_experiments.append(experiment.name)
# 		experiments.remove(experiment)

# print("Waiting to gain altitude...")
# while 18500 < altitude() < 70500: # first condition in case we don't reach orbit
# 	time.sleep(0.1)

# for experiment in experiments:
# 	print(f"Running {experiment.part.title}.")
# 	experiment.run()
# 	#experiment.transmit()

vessel.control.activate_next_stage()
