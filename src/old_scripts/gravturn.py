# Known issues:
# - sometimes BECO just doesn't happen and idk why

import krpc
import time
from krpc.platform import NAN
import utils
import math
import settings
import json
import os
import ast
import multiprocessing
import gravturn_worker
import queue

# turn_start_speed, turn_start_pitch, target_apoapsis, apoapsis_margin, num_srb_stages, has_fairing, has_payload
# ships = {
# 	"KPR Tom's Hairball": (20, 2.9, 90000, 100, 1, False, False), # TWR: 1.80
# 	"LLV Longcat's Night": (20, 4.6, 80000, -100, 1, True, True),
# }

if __name__ == '__main__':
	ships_filename = "gravturn_ships.json"

	def save_ships(data):
		with open(ships_filename, "w") as f:
			json.dump(data, f)	

	# Get ships
	if not os.path.exists(ships_filename) or os.path.getsize(ships_filename)==0:
		ships = {}
		save_ships(ships)
	else:
		with open(ships_filename, "r") as f:
			ships = json.load(f)

	# Connection setup
	conn = krpc.connect()
	vessel = conn.space_center.active_vessel
	conn.krpc.paused = True

	# Menu
	canvas = conn.ui.add_canvas()
	x_offset = 500
	is_recording = False

	mode_panel = canvas.add_panel()
	if vessel.name in ships:
		record_button = mode_panel.add_button("Record")
		load_button = mode_panel.add_button("Load")
		utils.arrange_elements((record_button, load_button), x_offset)
	else:
		record_button = mode_panel.add_button("Record")
		record_button.rect_transform.position = (x_offset, 0)

	record_panel = canvas.add_panel(False)
	record_labels = (
		record_panel.add_text("Target apoapsis:"),
		record_panel.add_text("Apoapsis drag offset:"),
		record_panel.add_text("Target inclination:"),
		record_panel.add_text("Turn start speed:"),
		record_panel.add_text("Turn start pitch:"),
		record_panel.add_text("Number of SRB stages:"),
		record_panel.add_text("Has fairing (y/n):"),
		record_panel.add_text("Has payload (y/n):"),
	)
	for label in record_labels:
		label.color = (255, 255, 255)
	record_fields = tuple(record_panel.add_input_field() for l in record_labels)
	if vessel.name in ships:
		for index, value in enumerate(ships[vessel.name]["record_values"]):
			record_fields[index].value = "y" if value is True else "n" if value is False else str(value)
	utils.arrange_elements_with_labels(conn, record_fields, record_labels, x_offset)
	record_launch_button = record_panel.add_button("Launch")
	record_back_button = record_panel.add_button("Back")
	record_launch_button.rect_transform.position = (x_offset, record_fields[-1].rect_transform.position[1]-record_fields[-1].rect_transform.size[1]-2)
	record_back_button.rect_transform.position = (x_offset, record_fields[-1].rect_transform.position[1]-record_fields[-1].rect_transform.size[1]*2-22)

	load_panel = canvas.add_panel(False)
	if vessel.name in ships:
		load_buttons = []
		for recording in ships[vessel.name]["recordings"]:
			load_buttons.append(load_panel.add_button(f"{recording['target_apoapsis']:,} m @ {recording['target_inclination']}°"))
		load_back_button = load_panel.add_button("Back")
		if load_buttons:
			utils.arrange_elements(load_buttons, x_offset)
			load_back_button.rect_transform.position = (x_offset, load_buttons[-1].rect_transform.position[1]-load_buttons[-1].rect_transform.size[1]-22)
		else:
			load_back_button.rect_transform.position = (x_offset, 0)

	def do_mode_panel():
		mode_panel.visible = True
		if vessel.name in ships:
			with conn.stream(getattr, record_button, "clicked") as record_clicked, conn.stream(getattr, load_button, "clicked") as load_clicked:
				while not (record_clicked() or load_clicked()):
					time.sleep(settings.wait_sleep)
				mode_panel.visible = False
				if record_clicked():
					record_button.clicked = False
					do_record_panel()
				else:
					load_button.clicked = False
					do_load_panel()
		else:
			with conn.stream(getattr, record_button, "clicked") as clicked:
				while not clicked():
					time.sleep(settings.wait_sleep)
			record_button.clicked = False
			mode_panel.visible = False
			do_record_panel()

	def do_record_panel():
		record_panel.visible = True
		with conn.stream(getattr, record_launch_button, "clicked") as launch_clicked, conn.stream(getattr, record_back_button, "clicked") as back_clicked:
			while not (launch_clicked() or back_clicked()):
				time.sleep(settings.wait_sleep)
			record_panel.visible = False
			if launch_clicked():
				# todo: validation
				if not vessel.name in ships:
					ships[vessel.name] = {}
				ships[vessel.name]["record_values"] = tuple(True if f.value=="y" else False if f.value=="n" else ast.literal_eval(f.value) for f in record_fields)
				if not "recordings" in ships[vessel.name]:
					ships[vessel.name]["recordings"] = []
				save_ships(ships)
				global is_recording
				is_recording = True
			else:
				record_back_button.clicked = False
				do_mode_panel()

	def do_load_panel():
		load_panel.visible = True
		streams = []
		for button in load_buttons:
			streams.append(conn.add_stream(getattr, button, "clicked"))
		with conn.stream(getattr, load_back_button, "clicked") as back_clicked:
			while True:
				for index, stream in enumerate(streams):
					if stream():
						recording = ships[vessel.name]["recordings"][index]
						global direction_data
						global other_data
						global values
						direction_data = iter(recording["direction_data"])
						other_data = iter(recording["other_data"])
						values = recording["values"]
						for stream in streams:
							stream.remove()
						load_panel.visible = False
						return
				if back_clicked():
					for stream in streams:
						stream.remove()
					load_panel.visible = False
					load_back_button.clicked = False
					do_mode_panel()
					break
				time.sleep(settings.wait_sleep)
	do_mode_panel()
	canvas.remove()
	conn.krpc.paused = False

	prograde_ref = conn.space_center.ReferenceFrame.create_hybrid(position=vessel.orbit.body.reference_frame, rotation=vessel.surface_reference_frame)

	(target_apoapsis, apoapsis_margin, target_inclination, turn_start_speed, turn_start_pitch, num_srb_stages, has_fairing, has_payload) = ships[vessel.name]["record_values"] if is_recording else values
	target_heading = 90 - target_inclination
	target_heading -= 3*math.cos(math.radians(target_heading)) # help compensate for rotation for non-equatorial orbits

	# Telemetry streams
	altitude = conn.add_stream(getattr, vessel.flight(), "mean_altitude")
	apoapsis = conn.add_stream(getattr, vessel.orbit, "apoapsis_altitude")
	periapsis = conn.add_stream(getattr, vessel.orbit, "periapsis_altitude")
	srf_speed = conn.add_stream(getattr, vessel.flight(vessel.orbit.body.reference_frame), "speed")
	prograde = conn.add_stream(getattr, vessel.flight(prograde_ref), "velocity")
	physics_warp_factor = conn.add_stream(getattr, conn.space_center, "physics_warp_factor")
	srb_fuel = [conn.add_stream(vessel.resources_in_decouple_stage(vessel.control.current_stage-x).amount, "SolidFuel") for x in range(2, 2+num_srb_stages)]

	# Prelaunch setup
	vessel.control.sas = False
	vessel.control.rcs = False
	vessel.control.throttle = 1
	srb_low_fuel_qty = [x() * 0.05 for x in srb_fuel]

	# Countdown
	utils.log(conn, "T-3...")
	time.sleep(1)
	utils.log(conn, "T-2...")
	time.sleep(1)
	utils.log(conn, "T-1...")
	if is_recording:
		queue = multiprocessing.JoinableQueue()
		process = multiprocessing.Process(target=gravturn_worker.worker, args=(queue,))
		process.start()
	time.sleep(1)

	utils.log(conn, "Launching.")
	vessel.control.activate_next_stage()
	vessel.auto_pilot.engage()
	vessel.auto_pilot.reference_frame = vessel.surface_reference_frame
	vessel.auto_pilot.target_roll = NAN
	vessel.auto_pilot.target_pitch_and_heading(90, target_heading)

	if is_recording:
		utils.log(conn, "Waiting until turn start speed.")
		while srf_speed() < turn_start_speed:
			time.sleep(settings.wait_sleep)

		utils.log(conn, "Starting gravity turn.")
		vessel.auto_pilot.target_pitch = 90-turn_start_pitch
		vessel.auto_pilot.wait()
		target_heading_x = math.sin(math.radians(90-turn_start_pitch)) # wait for prograde pitch to equal turn_start_pitch
		while utils.vec_normalize(prograde())[0] > target_heading_x:
			time.sleep(settings.wait_sleep)

		utils.log(conn, "Tracking prograde.")
		conn.space_center.physics_warp_factor = 2
	else:
		utils.log(conn, "Following prerecorded flight path.")
		next_direction = next(direction_data, None)
		next_other = next(other_data, None)
	num_srb_BECO = 0
	while apoapsis() < target_apoapsis+apoapsis_margin:
		if is_recording:
			vessel.auto_pilot.target_pitch = math.degrees(math.asin(utils.vec_normalize(prograde())[0]))
		else:
			current_altitude = altitude()
			if next_direction is not None and current_altitude >= next_direction[0]:
				vessel.auto_pilot.target_direction = next_direction[1]
				next_direction = next(direction_data, None)
			if next_other is not None and current_altitude >= next_other[0]:
				if next_other[1] == "start_physics_warp":
					conn.space_center.physics_warp_factor = 2
					next_other = next(other_data, None)
				else:
					raise ValueError("Unknown instruction "+str(next_other[1]))
		#print(num_srb_BECO, num_srb_stages)
		if num_srb_BECO < num_srb_stages:
			if physics_warp_factor() > 0 and srb_fuel[num_srb_BECO]() <= srb_low_fuel_qty[num_srb_BECO]:
				conn.space_center.physics_warp_factor = 0
			#print(srb_fuel[num_srb_BECO]())
			if srb_fuel[num_srb_BECO]() == 0:
				num_srb_BECO += 1
				utils.log(conn, f"BECO{' '+num_srb_BECO if num_srb_BECO < num_srb_BECO else ''}.")
				vessel.control.activate_next_stage()
				time.sleep(settings.warp_sleep)
				conn.space_center.physics_warp_factor = 2
		if physics_warp_factor() > 0 and apoapsis() >= target_apoapsis+apoapsis_margin-10000:
			conn.space_center.physics_warp_factor = 0
		time.sleep(0.0001) # intentionally not using settings.wait_sleep

	utils.log(conn, "MECO 1. Coasting out of atmosphere.")
	vessel.auto_pilot.reference_frame = vessel.surface_velocity_reference_frame
	vessel.auto_pilot.target_direction = (0, 1, 0)
	vessel.control.throttle = 0

	if is_recording:
		queue.put("END")
		queue.join() # wait for worker to send the data
		worker_data = queue.get()
		queue.close()
		queue.join_thread()
		if process.is_alive():
			process.terminate()

	time.sleep(settings.warp_sleep)
	conn.space_center.physics_warp_factor = 2
	while altitude() < 70100:
		if physics_warp_factor() > 0 and altitude() >= 69000:
			conn.space_center.physics_warp_factor = 0
		time.sleep(settings.wait_sleep)

	if has_fairing:
		utils.log(conn, "Separating fairing.")
		vessel.control.activate_next_stage()
		time.sleep(0.5)

	utils.circularize(conn, vessel)

	if is_recording:
		conn.krpc.paused = True
		canvas = conn.ui.add_canvas()
		save_button = canvas.add_button("Save recording")
		discard_button = canvas.add_button("Discard recording")
		utils.arrange_elements((save_button, discard_button), x_offset)
		with conn.stream(getattr, save_button, "clicked") as save_clicked, conn.stream(getattr, discard_button, "clicked") as discard_clicked:
			while not (save_clicked() or discard_clicked()):
				time.sleep(settings.wait_sleep)
			if save_clicked():
				ships[vessel.name]["recordings"].append({
					"target_apoapsis": target_apoapsis,
					"target_inclination": target_inclination,
					"direction_data": worker_data["direction_data"],
					"other_data": worker_data["other_data"],
					"values": ships[vessel.name]["record_values"]
				})
				save_ships(ships)
		canvas.remove()
		conn.krpc.paused = False

	if not has_payload:
		vessel.control.sas = True
	else:
		utils.log(conn, "Waiting to stabilize.")
		vessel.auto_pilot.disengage()
		vessel.control.sas = True
		time.sleep(4)

		utils.log(conn, "Separating booster.")
		booster = vessel.control.activate_next_stage()[0]
		time.sleep(3)

		utils.log(conn, "Deorbiting booster.")
		booster.control.sas = False
		booster.auto_pilot.engage()
		booster.auto_pilot.reference_frame = booster.orbital_reference_frame
		booster.auto_pilot.target_direction = (0, -1, 0)
		booster.auto_pilot.wait()
		booster.auto_pilot.wait()
		booster.control.throttle = 1
		booster.control.sas = True
