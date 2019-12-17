''' Charles R Brunstad
	Project Hacking, in the Time Domain

	Simulator bandwidth was updated to more accurately reflect bandwidth
	in silico, and wires between nodes are now unidirectional.

	12/14/19

	In this update, we see the introduction of centiticks and channels—-a
	formalization of the level of quantization we're attempting to introduce.
	Rudimentary calculations were performed to determine both the speed with
	which data should traverse the grid and the bandwidth with which they
	should do so. It was found that, on average, to meet the 15-tick deadline
	for each spike, a packet should take no longer than 11 centiticks (ct, one-
	hundredth of a tick, or 1/100th of a ms) to traverse one core. As for
	bandwidth, the paper states that TrueNorth can achieve little congestion
	at 2500 spikes/ticks on all ports for a given core. This implies that
	each direction (NSEW) can handle roughly 600 spikes/tick, or 6 spikes/ct.
	If we take it that each "channel" of communication can transfer a packet
	in 1 ct, 6 spikes/direction/ct implies that each line consists of 6
	said channels.

	Also, as suggested in the previous update, a finer level of granularity was
	introduced to the routing system. Packets that are "turning the corner"
	now traverse routers with lesser speed and encounter more potential
	bottlenecks in a way that is far more faithful to the TrueNorth
	architecture.

	Additionally, the simulation algorithm was updated not only to accomodate
	each of the above new features, but also to increase speed. The updated
	algorithm is reproduced below.

		for each packet:
			decrement delay by one time unit
		to_visit = []
		for each packet:
			if packet.parent_component is a line and delay == 0:
				if packet.dx > 0:
					add packet to component_2's wait buffer
				elif packet.dx < 0:
					add packet to component_1's wait buffer
				elif packet.dy > 0:
					add packet to component_1's wait buffer
				elif packet.dy < 0:
					add packet to component_2's wait buffer
				set packet wait time
			if packet.parent_component is a core and packet.parent_component is
						not in to_visit:
				append packet.parent_component to to_visit
		for each core in to_visit:
				for each packet in the send buffer:
					add to directional packet_out register if register is empty
							else return to send buffer
				for each packet in the wait buffer:
					add to directional packet_out register if register is empty
							else send to send buffer
		for each core in to_visit, selected randomly:
			for each packet in the packet_out_buffer:
				offload packet to corresponding wire
				packet.parent_component.packet_out_buffer[packet] = wire

	Next, simulation workloads—-both synthetic and quasi-faithful to those
	generated in typical SNN environments—-will be applied to answer a
	multitude of questions. For example, how does changing the network topology
	affect congestion? How much traffic must be generated for packet loss? What
	is the saturation point?

	11/21/19

	In this update to the TrueNorth core simulator, the simulation algorithm
	was altered so as to be entirely event-driven. More specifically, each
	packet is now maintained in a list, and components are "visited" by the
	algorithm at timestep t if and only if they are involved in processing a
	packet at t.

		for each packet:
			decrement delay by one time unit
		for each packet:
			if packet.parent_component is a line and delay == 0:
				if packet.dx > 0:
					add packet to component_2's wait buffer
				elif packet.dx < 0:
					add packet to component_1's wait buffer
				elif packet.dy > 0:
					add packet to component_1's wait buffer
				elif packet.dy < 0:
					add packet to component_2's wait buffer
		for each packet:
			visited = []
			if packet.parent_component is a core and packet.parent_component is
						not in visited:
				append packet.parent_component to visited
				for each packet in the send buffer:
					add to directional packet_out register if register is empty
							else return to send buffer
					packet.ready_to_send = True
				for each packet in the wait buffer:
					add to directional packet_out register if register is empty
							else send to send buffer
					packet.ready_to_send = True
		for each packet, selected at random:
			if packet.ready_to_send:
				offload packet to corresponding wire
				packet.ready_to_send = False
				packet.parent_component.packet_out_buffer[packet] = None

	In the fourth iteration over all packets, same-time injection is
	arbitrated randomly. That is, if packets a and b are queued for injection
	to wire w at timestep t, a and b have the same probability p = 0.5 of being
	injected into w.

	Several features are to be added by the next update.

	First, because each core has two bidirectional ports for each direction,
	wire bandwidth will be implemented. In this vein, how would one approximate
	the available wire bandwidth in terms of packets--given that there doesn't
	seem to be any concrete data available in the paper?

	Second, the current version of this simulator does not appropriately
	arbitrate between packets arriving at the same time. In a true TrueNorth
	core, a packet traveling in the North/South and East/West directions
	encounters exactly one forwarding unit with one arbiter built-into a
	merge block. A packet "turning the corner," however, encounters two such
	units. It's also important to note that, upon removal from the routing
	network, all packets are subject to an additional nondeterministic merge
	block. The current scheme, on the other hand, simply blocks packets for
	a predetermined amount of time, and will be updated to reflect the
	possibilities of complex blocking.

	Finally, a significant amount of time was dedicated to reading Dally and
	Towles, especially the chapters on flow control. It is hoped that the
	application of backpressure to input channels—-potentially even all the
	way back to the generating core--may be implemented.


	11/14/19

	Many improvements were made in this update to the TrueNorth core simulator.

	First, the simulation algorithm was formalized so as to better guide
	implementation specifics. It is reproduced below:

		for each wire:
			if contains a packet:
				decrement delay by one time unit
		for each core:
			for each wire, selected randomly:
				if wire contains a packet:
					if core can help route packet:
						add to wait buffer
		for each core:
			decrement all stall timers for waiting packets
			for each packet in the send buffer:
				add to directional packet_out register if register is empty
			for each packet in the wait buffer:
				add to directional packet_out register if register is empty
			offload packet_out registers to adjacent wires
			reset all packet_out registers

	Three discrete loops—-one for each core--are required because otherwise,
	for a given core c at a given timestep t, whether a wire w is cleared
	before a new packet is injected into w is a function of when c is visited
	within timestep t.

	Wires are selected randomly so as to better mimic the non-deterministic
	process of merging packets that arrive almost simultaneously.

	Additionally, it was decided that cores should be able to send out a packet
	in every possible direction at each timestep. Packets are first taken from
	the send_buffer, as these packets have already been stalled in the
	wait_buffer. Packets from either the send_buffer or the wait_buffer that
	are still blocked from being routed are returned or sent to the
	send_buffer.

	Also, packets that attempt to route off the edge of the array are
	destroyed.

	Finally, a number of tests were devised so as to demonstrate the
	time-domain-centric nature of the simulator and to determine correctness.
	The packets injected into the system were propagated as expected.

	11/7/19

	Although my weekend was a bit consumed by trips to the emergency department
	owing to a nasty illness, I've managed to read the assigned papers and have
	hacked up the following simulator that operates in the time domain. In this
	toy run, an 8x8 2D mesh of cores are instantiated, and a set of packets are
	injected at select locations and allowed to propagate throughout the
	network. Different delays are associated with transit through wires and
	through cores so as to more appropriately model the TrueNorth chip.

	Routing multiple packets through the same core incurs a time penalty for
	the lagging packet(s), as only one packet can be transmitted through a
	given line at a time.

	Currently, the simulator will allow a chip to send out only a single packet
	during a given timestep, although it is reasonable for a chip to begin
	transmitting up to four packets at the same time--onto distinct wires.

	Additionally, I wanted to thank you for the reading recommendations you
	sent my way. I've read several chapters from Principles and Practices of
	Interconnection Networks, and I believe it will serve as an invaluable
	resource in the future. I've also begun to look into the other papers you
	forwarded to me, and I think looking into the Flattened Butterfly topology,
	as well as Valiant routing, would be really fruitful.
'''

from collections import deque
import random
import argparse

N_CHANNELS = 1

class Packet:
	id = 1
	delays = 0

	def __init__(self, parent, dx, dy, dz = 0):
		self.dx = dx
		self.dy = dy
		self.dz = dz
		self.routing_delay = 0
		self.name = Packet.id
		self.parent = parent
		self.directionality = self.determine_directionality()
		self.ready_to_send = False
		Packet.id += 1

	def determine_directionality(self):
		'''	Priority: x, then y, then z
		'''
		directionality = "upbound" if self.dz > 0 else "downbound"
		directionality = "southbound" if self.dy < 0 else directionality
		directionality = "northbound" if self.dy > 0 else directionality
		directionality = "eastbound" if self.dx > 0 else directionality
		directionality = "westbound" if self.dx < 0 else directionality
		return directionality

class Hardware:
	def __init__(self):
		self.default_routing_delay = 0	# default to no processing time

class Buffer:
	def __init__(self):
		self.out = [None for x in range(0, N_CHANNELS)]

	def is_clear(self):
		for x in range(0, N_CHANNELS):
			if self.out[x] == None:
				return True
		return False

	def add(self, packet):
		for x in range(0, N_CHANNELS):
			if self.out[x] == None:
				self.out[x] = packet
				break
		#self._count_capacity()

	def _count_capacity(self):
		count = 0
		for packet in self.out:
			if packet != None:
				count += 1
		print("Buffer contains " + str(count) + " packets")

	def clear(self):
		for x in range(0, N_CHANNELS):
			self.out[x] = None

	def flush(self):
		packets = []
		for packet in self.out:
			if packet != None:
				packets.append(packet)
		self.clear()
		return packets

class Core(Hardware):
	id = 1

	def __init__(self, n1, n2, e1, e2, w1, w2, s1, s2, u1 = None, u2 = None, d1 = None, d2 = None):
		self.lines_in = [n1, e1, w1, s1, u1, d1]
		self.lines_out = [n2, e2, w2, s2, u2, d2]
		self.default_routing_delay = 2 # overhead of bundling and unbundling: page 1547
		self.send_buffer = deque()	# used if cannot inject a packet to a transmission line
		self.wait_buffer = deque()	# used to stall so that default routing delay ticks to 0
		self.name = Core.id
		self.packet_out_buffer = [Buffer() for x in range(0, 6)]
		self.forward_north_merge = None
		self.forward_east_merge = None
		self.forward_south_merge = None
		self.forward_west_merge = None
		self.forward_up_merge = None
		self.forward_down_merge = None
		Core.id += 1

	def inject(self, packet):
		packet.routing_delay = self.default_routing_delay
		packet.parent = self
		self.wait_buffer.append(packet)

	def route(self):
		'''	Prepare a packet for sendoff, either taken directly from the send buffer, or taken
			from the wait buffer (provided nothing's been queued in the send buffer)
			Packets should have an average transit time/core of ~11.5 centiticks
				11 - 1 (for wire) = 10 - (2 * 2) (for entry/exit overhead) = 6
				Might have to turn the corner, increasing average
		'''
		# send buffer has higher priority than wait buffer
		# add unroutable packets back to the buffer
		new_wait_buffer = deque()
		new_buffer = deque()
		while len(self.send_buffer) > 0:
			packet = self.forward(self.send_buffer.popleft())
			if packet:
				new_buffer.append(packet)
		self.send_buffer = new_buffer

		for packet in self.wait_buffer:
			if packet.routing_delay > 0:
				packet.routing_delay -= 1
				new_wait_buffer.append(packet)
			else:
				packet, is_outbound = self.advance(packet)	# send to next internal component
				if is_outbound:
					#print("Packet " + str(packet.name) + " is at core " + str(self.name) + " and dx = " + str(packet.dx) + ", dy = " + str(packet.dy) + ", dz = " + str(packet.dz))
					blocked_packet = self.forward(packet)
					if blocked_packet:
						Packet.delays += 1
						self.send_buffer.append(blocked_packet)
				else:
					new_wait_buffer.append(packet)
		self.wait_buffer = new_wait_buffer

		self.clear_merges()

	def advance(self, packet):
		''' Responsible for forwarding a packet through a given routing subsystem
		'''
		is_outbound = False
		if "exit" in packet.directionality:
			return (packet, True)
		packet.routing_delay = 6
		if packet.directionality == 'eastbound':
			if self.forward_east_merge == None:
				self.forward_east_merge = packet
				if packet.dx != 0:
					packet.directionality = 'east-exit'
				elif packet.dy > 0:
					packet.directionality = 'north'
				else:
					packet.directionality = 'south'	# route exits and up/downs through forward-south
			else:
				packet.routing_delay = 0	# unsuccessful routes can be immediately reattempted
				Packet.delays += 1
		elif packet.directionality == 'westbound':
			if self.forward_west_merge == None:
				self.forward_west_merge = packet
				if packet.dx != 0:
					packet.directionality = 'west-exit'
				elif packet.dy > 0:
					packet.directionality = 'north'
				else:
					packet.directionality = 'south'
			else:
				packet.routing_delay = 0
				Packet.delays += 1
		elif "south" in packet.directionality:	# accept both southbound packets and packets turning the corner
			if self.forward_south_merge == None:
				self.forward_south_merge = packet
				if packet.dy != 0:
					packet.directionality = 'south-exit'
				elif packet.dz > 0:
					packet.directionality = 'up'
				elif packet.dz < 0:
					packet.directionality = 'down'
				else:
					packet.directionality = 'self-exit'
			else:
				packet.routing_delay = 0
				Packet.delays += 1
		elif "north" in packet.directionality:	# accept both northbound packets and packets turning the corner
			if self.forward_north_merge == None:
				self.forward_north_merge = packet
				if packet.dy != 0:
					packet.directionality = 'north-exit'
				elif packet.dz > 0:
					packet.directionality = 'up'
				elif packet.dz < 0:
					packet.directionality = 'down'
				else:
					packet.directionality = 'self-exit'
			else:
				packet.routing_delay = 0
				Packet.delays += 1
		elif "up" in packet.directionality:	# accept both southbound packets and packets turning the corner
			if self.forward_up_merge == None:
				self.forward_up_merge = packet
				packet.directionality = 'up-exit'
			else:
				packet.routing_delay = 0
				Packet.delays += 1
		elif "down" in packet.directionality:	# accept both northbound packets and packets turning the corner
			if self.forward_down_merge == None:
				self.forward_down_merge = packet
				packet.directionality = 'down-exit'
			else:
				packet.routing_delay = 0
				Packet.delays += 1
		return (packet, is_outbound)

	def clear_merges(self):
		self.forward_north_merge = None
		self.forward_east_merge = None
		self.forward_south_merge = None
		self.forward_west_merge = None
		self.forward_up_merge = None
		self.forward_down_merge = None

	def send_out(self):
		for x in range(0, len(self.lines_out)):
			if self.lines_out[x]:
				packets = self.packet_out_buffer[x].flush()
				for packet in packets:
					blocked_packet = self.lines_out[x].inject(packet)
					if blocked_packet != None:	# add packet back in if it was blocked
						Packet.delays += 1
						self.packet_out_buffer[x].add(blocked_packet)

	def forward(self, packet):
		''' Adds packets to the appropriate directional output if possible
			Returns packets that it cannot route at the present time
		'''
		if packet.dx > 0:	# send east
			if not self.lines_out[1]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if self.lines_out[1].is_clear() and self.packet_out_buffer[1].is_clear():
				self.packet_out_buffer[1].add(packet)
				return None
		elif packet.dx < 0:	# send west
			if not self.lines_out[2]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if self.lines_out[2].is_clear() and self.packet_out_buffer[2].is_clear():
				self.packet_out_buffer[2].add(packet)
				return None
		elif packet.dy > 0:	# send north
			if not self.lines_out[0]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if self.lines_out[0].is_clear() and self.packet_out_buffer[0].is_clear():
				self.packet_out_buffer[0].add(packet)
				return None
		elif packet.dy < 0: # send south
			if not self.lines_out[3]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if self.lines_out[3].is_clear() and self.packet_out_buffer[3].is_clear():
				self.packet_out_buffer[3].add(packet)
				return None
		elif packet.dz > 0:	# send up
			if not self.lines_out[4]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if self.lines_out[4].is_clear() and self.packet_out_buffer[4].is_clear():
				self.packet_out_buffer[4].add(packet)
				return None
		elif packet.dz < 0: # send down
			if not self.lines_out[5]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if self.lines_out[5].is_clear() and self.packet_out_buffer[5].is_clear():
				self.packet_out_buffer[5].add(packet)
				return None
		else:
			# Destroy packet
			#print("Packet " + str(packet.name) + " has reached its destination")
			packet.parent = None
			return None
		return packet

class Line(Hardware):
	''' Bandwidth.
			One wire in/one wire out for each direction. N_CHANNELS = 1
	'''
	id = 1

	def __init__(self):
		self.default_routing_delay = 1 # 1 timesteps to move a packet across a wire
		self.name = Line.id
		Line.id += 1
		self.component_in = None
		self.component_out = None
		self.channels = [None for x in range(0, N_CHANNELS)]

	def is_clear(self):
		for channel in self.channels:
			if channel == None:
				return True
		return False

	def inject(self, packet):
		'''	Inject packet into one of the open channels
			Return the packet if it cannot be injected
		'''
		for channel in self.channels:
			if channel == None:
				channel = packet
				packet.parent = self
				packet.routing_delay = self.default_routing_delay
				return None
		return packet

	def connect(self, terminus_1, terminus_2):
		'''	Connect the components so that the line can forward
			packets appropriately
		'''
		self.component_in = terminus_1
		self.component_out = terminus_2

	def dissassociate(self, packet):
		''' Clear the channel of the packet for future routing
		'''
		for channel in self.channels:
			if channel == packet:
				channel = None

def simulate(workload, timesteps, probability, width, topology, topology_type, mean_distance):
	'''	Make each component perform its duty per timestamp
		for each packet:
			decrement delay by one time unit
		to_visit = []
		for each packet:
			if packet.parent_component is a line and delay == 0:
				if packet.dx > 0:
					add packet to component_2's wait buffer
				elif packet.dx < 0:
					add packet to component_1's wait buffer
				elif packet.dy > 0:
					add packet to component_1's wait buffer
				elif packet.dy < 0:
					add packet to component_2's wait buffer
				set packet wait time
			if packet.parent_component is a core and packet.parent_component is
						not in to_visit:
				append packet.parent_component to to_visit
		for each core in to_visit:
				for each packet in the send buffer:
					add to directional packet_out register if register is empty
							else return to send buffer
				for each packet in the wait buffer:
					add to directional packet_out register if register is empty
							else send to send buffer
		for each core in to_visit, selected randomly:
			for each packet in the packet_out_buffer:
				offload packet to corresponding wire
				packet.parent_component.packet_out_buffer[packet] = wire

		These four steps need to be computed discretely for each core because
		otherwise, for a given core c, whether a wire w is cleared before a
		new packet is injected into w is a function of when c is to_visit.
	'''
	packets = []
	distance = 0
	if workload == "toy" and topology_type == 'mesh':
		packets = toy_run(topology)
	elif workload == "toy" and topology_type == '3Dmesh':
		packets = toy_run3D(topology)
	for t in range(0, timesteps):
		if t % 10 == 0:
			print(t)
		if workload == 'random':
			new_packets, new_distance = random_firestorm(topology, topology_type, probability, width, mean_distance)	# add in new batch of packets
			packets += new_packets
			distance += new_distance
		for packet in packets:
			if isinstance(packet.parent, Line):
				packet.routing_delay = max(0, packet.routing_delay - 1)
		to_visit = []
		for packet in packets:
			if isinstance(packet.parent, Line) and packet.routing_delay == 0:
				packet.parent.dissassociate(packet)
				if packet.dx > 0 and packet.parent.component_out:
					packet.dx -= 1
					packet.directionality = 'eastbound'
				elif packet.dx < 0 and packet.parent.component_out:
					packet.dx += 1
					packet.directionality = 'westbound'
				elif packet.dy > 0 and packet.parent.component_out:
					packet.dy -= 1
					packet.directionality = 'northbound'
				elif packet.dy < 0 and packet.parent.component_out:
					packet.dy += 1
					packet.directionality = 'southbound'
				elif packet.dz > 0 and packet.parent.component_out:
					packet.dz -= 1
					packet.directionality = 'upbound'
				elif packet.dz < 0 and packet.parent.component_out:
					packet.dz += 1
					packet.directionality = 'downbound'
				if packet.parent.component_out:
					packet.parent.component_out.inject(packet)
			if isinstance(packet.parent, Core) and packet.parent not in to_visit:
				to_visit.append(packet.parent)
		for core in to_visit:
			core.route()
		random.shuffle(to_visit)
		for core in to_visit:
			core.send_out()
	print("total distance traveled: " + str(distance))

def construct_mesh(n_cores):
	width = round(n_cores ** (1 / 2))
	core_array = [[None for x in range(0, width)] for y in range(0, width)]
	for x in range(0, width):
		east = [None, None]
		west = [None, None]
		north = [None, None]
		south = [None, None]
		for y in range(0, width):
			south = [None, None] if x == width - 1 else [Line(), Line()]
			north = [None, None] if x == 0 else [core_array[x - 1][y].lines_out[3], core_array[x - 1][y].lines_in[3]]
			east = [Line(), Line()] if y < width - 1 else [None, None]
			west = [None, None] if y == 0 else [core_array[x][y - 1].lines_out[1], core_array[x][y - 1].lines_in[1]]
			core_array[x][y] = (Core(north[0], north[1], east[0], east[1], west[0], west[1], south[0], south[1]))

	for x in range(0, width - 1):
		for y in range(0, width - 1):
			# all lines now "know" connected cores
			core_array[x][y].lines_out[1].connect(core_array[x][y], core_array[x][y + 1]) # east --> next column over
			core_array[x][y].lines_in[1].connect(core_array[x][y + 1], core_array[x][y]) # east --> next column over
			core_array[x][y].lines_out[3].connect(core_array[x][y], core_array[x + 1][y]) # south --> next row over
			core_array[x][y].lines_in[3].connect(core_array[x + 1][y], core_array[x][y]) # south --> next row over
	return core_array

def construct_3D_mesh(n_cores):
	width = round(n_cores ** (1 / 3))
	mesh = [[[None for x in range(0, width)] for y in range(0, width)] for z in range(0, width)]
	for z in range(0, width):
		for x in range(0, width):
			for y in range(0, width):
				# build z downwards
				south = [None, None] if x == width - 1 else [Line(), Line()]
				north = [None, None] if x == 0 else [mesh[x - 1][y][z].lines_out[3], mesh[x - 1][y][z].lines_in[3]]
				east = [Line(), Line()] if y < width - 1 else [None, None]
				west = [None, None] if y == 0 else [mesh[x][y - 1][z].lines_out[1], mesh[x][y - 1][z].lines_in[1]]
				down = [Line(), Line()] if z < width - 1 else [None, None]
				up = [None, None] if z == 0 else [mesh[x][y][z - 1].lines_out[5], mesh[x][y][z - 1].lines_in[5]]
				mesh[x][y][z] = (Core(north[0], north[1], east[0], east[1], west[0], west[1], south[0], south[1], up[0], up[1], down[0], down[1]))

	for x in range(0, width):
		for y in range(0, width):
			for z in range(0, width - 1):
				# all lines now "know" connected cores
				if x < width - 1 and y < width - 1:
					mesh[x][y][z].lines_out[1].connect(mesh[x][y][z], mesh[x][y + 1][z]) # east --> next column over
					mesh[x][y][z].lines_in[1].connect(mesh[x][y + 1][z], mesh[x][y][z]) # east --> next column over
					mesh[x][y][z].lines_out[3].connect(mesh[x][y][z], mesh[x + 1][y][z]) # south --> next row over
					mesh[x][y][z].lines_in[3].connect(mesh[x + 1][y][z], mesh[x][y][z]) # south --> next row over
				mesh[x][y][z].lines_out[5].connect(mesh[x][y][z], mesh[x][y][z + 1]) # down --> core here feeds down one level
				mesh[x][y][z].lines_in[5].connect(mesh[x][y][z + 1], mesh[x][y][z]) # down --> core down one level feeds in
	return mesh

def toy_run(core_array):

	 # These packets intersect at core 1, 1 and neither gets delayed because their routing pipelines do not overlap
	packets = []
	packets.append(Packet(core_array[0][1], 0, -5))
	packets.append(Packet(core_array[1][0], 4, 1))

	 # Only one of these packets can be sent east first
	packets.append(Packet(core_array[0][0], 4, -1))
	packets.append(Packet(core_array[0][0], 4, -1))

	 # Only one of these packets can be sent west first
	packets.append(Packet(core_array[4][4], -2, -2))
	packets.append(Packet(core_array[4][4], -1, -2))

	 # These packets meet at an intermediate core but do not conflict because their routing pipelines do not overlap
	packets.append(Packet(core_array[2][10], 0, -5))
	packets.append(Packet(core_array[4][10], 0, 3))

	 # These packets meet at an intermediate core but might experience a merge delay
	packets.append(Packet(core_array[10][10], 0, -5))
	packets.append(Packet(core_array[11][11], -1, -5))

	 # This packet travels off-grid and is lost
	packets.append(Packet(core_array[0][10], 0, 5))

	for packet in packets:
		packet.parent.inject(packet)
	return packets

def toy_run3D(mesh):
	 # These packets intersect at core 1, 1 and neither gets delayed because their routing pipelines do not overlap
	packets = []
	#packets.append(Packet(mesh[0][1][0], 0, -5, -5))
	#packets.append(Packet(mesh[1][0][0], 4, 0, -5))

	packets.append(Packet(mesh[15][15][0], 0, 0, -5))
	print(mesh[15][15][0].lines_out[5].component_out)
	print(mesh[14][14][0].lines_out[5].component_out)

	print(mesh[15][15][0].lines_in[5].component_out)
	print(mesh[14][14][0].lines_in[5].component_out)

	for packet in packets:
		packet.parent.inject(packet)
	return packets

def random_firestorm(topology, topology_type, probability, width, mean_distance):
	''' Generate packets for each neuron with p = probability and address them
		to valid cores such that, on average, the mean_distance value roughly
		approximates mean distance traveled by each packet in each direction
	'''
	packets = []
	total_distance = 0
	if topology_type == '3Dmesh':
		for x in range(0, width):
			for y in range(0, width):
				for z in range(0, width):
					for n in range(0, 256):
						r_val = random.random()
						if r_val < probability:
							min_x = max(0, -mean_distance * 2 + y) - y
							max_x = min(width - 1, y + (mean_distance * 2)) - y
							max_y = min(width - 1, mean_distance * 2 + x) - x
							min_y = max(0, x - (mean_distance * 2)) - x
							min_z = max(-(width - 1 - z), -mean_distance * 2)
							max_z = min(mean_distance * 2, z)
							x_val = random.randint(min_x, max_x)
							y_val = random.randint(-max_y, -min_y)
							z_val = random.randint(min_z, max_z)
							packet = Packet(topology[x][y][z], x_val, y_val, z_val)
							packets.append(packet)
							#print(packet.name, ":", x, y, z, min_z, max_z, width, x_val, y_val, z_val)
							total_distance += abs(x_val)
							total_distance += abs(y_val)
							total_distance += abs(z_val)
	elif topology_type == 'mesh':
		for x in range(0, width):
			for y in range(0, width):
				for n in range(0, 256):
					r_val = random.random()
					if r_val < probability:
						min_x = max(0, -mean_distance * 2 + y) - y
						max_x = min(width - 1, y + (mean_distance * 2)) - y
						max_y = min(width - 1, mean_distance * 2 + x) - x
						min_y = max(0, x - (mean_distance * 2)) - x
						x_val = random.randint(min_x, max_x)
						y_val = random.randint(-max_y, -min_y)
						packet = Packet(topology[x][y], x_val, y_val)
						packets.append(packet)
						#packet = Packet(topology[x][y], random.randint(-mean_distance * 2, mean_distance * 2), random.randint(-mean_distance * 2, mean_distance * 2))
						#packets.append(packet)
						total_distance += abs(x_val)
						total_distance += abs(y_val)

	for packet in packets:
		packet.parent.inject(packet)
	return (packets, total_distance)

def quasi_SNN_firestorm(topology, topology_type, probability, width):
	''' Generate spikes from a given neuron with p = probability and address it
		to a core so as to mimic a SNN's true function.
		Map
	'''
	

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Simulate the TrueNorth chip.')
	parser.add_argument('--topology', dest='topology_type', default='mesh')
	parser.add_argument('--workload', dest='workload', default='toy')
	parser.add_argument('--n_cores', type=int, dest='n_cores', default=4096)
	parser.add_argument('--t', type=int, dest='time', default=100)
	parser.add_argument('--distance', type=int, dest='mean_distance', default=1)	# gives distance an average packet will have to travel in each direction
	parser.add_argument('--probability', type=float, dest='probability', default=0.0001)	# gives probability that a given neuron will fire in random workload
	args = parser.parse_args()
	topology_type = args.topology_type
	workload = args.workload
	n_cores = args.n_cores
	time = args.time
	probability = args.probability
	mean_distance = args.mean_distance
	topology = None
	width = None
	if topology_type == "mesh":
		topology = construct_mesh(n_cores)
		width = round(n_cores ** (1 / 2))
	elif topology_type == "3Dmesh":
		topology = construct_3D_mesh(n_cores)
		width = round(n_cores ** (1 / 3))
	simulate(workload, time, probability, width, topology, topology_type, mean_distance)
	print("Total number of packet delays: " + str(Packet.delays))



