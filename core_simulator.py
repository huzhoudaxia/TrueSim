''' Charles R Brunstad
	Project Hacking, in the Time Domain
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

INDICES = [0, 1, 2, 3]

class Packet:
	id = 1

	def __init__(self, dx, dy):
		self.dx = dx
		self.dy = dy
		self.hops = 0	# metrics
		self.delays = 0	# metrics
		self.routing_delay = 0
		self.name = Packet.id
		self.parent = None
		self.ready_to_send = False
		Packet.id += 1

class Hardware:
	def __init__(self):
		self.default_routing_delay = 0	# default to no processing time

class Core(Hardware):
	id = 1

	def __init__(self, north_line, east_line, west_line, south_line):
		self.lines = [north_line, east_line, west_line, south_line]
		self.default_routing_delay = 25
		self.send_buffer = deque()	# used if cannot inject a packet to a transmission line
		self.wait_buffer = deque()	# used to stall so that default routing delay ticks to 0
		self.name = Core.id
		self.packet_out_buffer = [None, None, None, None]
		self.merge_delay = 2
		Core.id += 1

	def enq(self, packet):
		self.wait_buffer.append(packet)

	def route(self, packet):
		packet.routing_delay = self.default_routing_delay
		self.wait_buffer.append(packet)

	def old_route(self):
		'''	Route a packet, either taken directly from the send buffer, or taken
			from the wait buffer (provided nothing's been queued in the send buffer)
		'''
		# send buffer has higher priority than wait buffer
		# add unroutable packets back to the buffer
		to_remove = []
		new_buffer = deque()
		while len(self.send_buffer) > 0:
			packet = self.forward(self.send_buffer.popleft())
			if packet:
				new_buffer.append(packet)
		self.send_buffer = new_buffer

		for packet in self.wait_buffer:
			if packet.routing_delay > 0:
				packet.routing_delay -= 1
			else:
				print("Packet " + str(packet.name) + " is at core " + str(self.name) + " and must travel " + str(packet.dx) + " cores in the x and " + str(packet.dy) + " cores in the y")
				to_remove.append(packet)
				blocked_packet = self.forward(packet)
				if blocked_packet:
					self.send_buffer.append(blocked_packet)

		for packet in to_remove:
			self.wait_buffer.remove(packet)

		for x in range(0, 4):
			if self.lines[x] and self.packet_out_buffer[x]:
				self.lines[x].inject(self.packet_out_buffer[x])

		self.packet_out_buffer = [None, None, None, None]

	def forward(self, packet):
		''' Adds packets to the appropriate directional output if possible
			Returns packets that it cannot route at the present time
		'''
		if packet.dx > 0:	# send east
			if not self.lines[1]:
				print("Packet " + str(packet.name) + " was lost")
				return None 	# destroy packets that attempt to go off the edge
			if not self.lines[1].packet and not self.packet_out_buffer[1]:
				self.packet_out_buffer[1] = packet
				return None
		elif packet.dx < 0:	# send west
			if not self.lines[2]:
				print("Packet " + str(packet.name) + " was lost")
				return None 	# destroy packets that attempt to go off the edge
			if not self.lines[2].packet and not self.packet_out_buffer[2]:
				self.packet_out_buffer[2] = packet
				return None
		elif packet.dy > 0:	# send north
			if not self.lines[0]:
				print("Packet " + str(packet.name) + " was lost")
				return None 	# destroy packets that attempt to go off the edge
			if not self.lines[0].packet and not self.packet_out_buffer[0]:
				self.packet_out_buffer[0] = packet
				return None
		elif packet.dy < 0: # send south
			if not self.lines[3]:
				print("Packet " + str(packet.name) + " was lost")
				return None 	# destroy packets that attempt to go off the edge
			if not self.lines[3].packet and not self.packet_out_buffer[3]:
				self.packet_out_buffer[3] = packet
				return None
		else:
			# Destroy packet
			print("Packet " + str(packet.name) + " has reached its destination")
			return None
		return packet


	def pickup(self):
		''' Grab new packets from connected lines, but only if they're headed in
			a direction that this core can help with (i.e. continue sending to
			the north if packet came from the south, but a core should do nothing
			if a packet lies to a core's south and has a destination to the south)

			NOT ADHERED TO
			Merging routes cause packets to be delayed non-deterministically. The
			following sets of routes are merging:
				West --> North + South --> North
				East --> North + South --> North

				North --> South + East --> South
				North --> South + West --> South
			Because travel in the x-direction is prioritized over travel in the
			y-direction, no merging routes exist for packets heading East/West.

		'''
		random.shuffle(INDICES)
		for x in INDICES:
			line = self.lines[x]
			if line and line.packet and line.packet.routing_delay == 0 and \
					((line.packet.dx > 0 and x == 2) or \
					(line.packet.dx < 0 and x == 1)  or \
					(line.packet.dy > 0 and x == 3) or \
					(line.packet.dy < 0 and x == 0)):
				line.packet.routing_delay = self.default_routing_delay
				if x == 2:
					line.packet.dx -= 1
				elif x == 1:
					line.packet.dx += 1
				elif x == 3:
					line.packet.dy -= 1
				elif x == 0:
					line.packet.dy += 1
				self.wait_buffer.append(line.packet)
				line.packet = None


class Line(Hardware):
	id = 1

	def __init__(self):
		self.packet = None
		self.default_routing_delay = 3 # 3 timesteps to move a packet across a wire
		self.name = Line.id
		Line.id += 1
		self.component_1 = None
		self.component_2 = None

	def inject(self, packet):
		self.packet = packet
		self.packet.routing_delay = self.default_routing_delay

	def connect(self, terminus_1, terminus_2):
		self.component_1 = terminus_1
		self.component_2 = terminus_2

	def route(self):
		if self.packet:
			if self.packet.routing_delay > 0:
				self.packet.routing_delay -= 1

def simulate(packets, timesteps):
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

		These four steps need to be computed discretely for each core because
		otherwise, for a given core c, whether a wire w is cleared before a
		new packet is injected into w is a function of when c is to_visit.
	'''
	for packet in packets:
		if isInstance(packet.parent, Line):
			packet.routing_delay = max(0, packet.routing_delay - 1)
	to_visit = []
	for packet in packets:
		if isInstance(packet.parent, Line) and packet.routing_delay == 0:
			if packet.dx > 0:
				packet.parent.component_2.route(packet)
			elif packet.dx < 0:
				packet.parent.component_1.route(packet)
			elif packet.dy > 0:
				packet.parent.component_1.route(packet)
			elif packet.dy < 0:
				packet.parent.component_2.route(packet)
		if isInstance(packet.parent, Core) and packet.parent_component not in to_visit:
			to_visit.append(packet.parent)


	#for t in range(0, timesteps):
	#	print("t = " + str(t))
	#	visited = {}
	#	for x in range(0, len(core_array)):
	#		for y in range(0, len(core_array[0])):
	#			core = core_array[x][y]
	#			for line in core.lines:
	#				if line and not visited.get(line):
	#					line.route()
	#					visited[line] = True
	#	for x in range(0, len(core_array)):
	#		for y in range(0, len(core_array[0])):
	#			core = core_array[x][y]
	#			core.pickup()
	#	for x in range(0, len(core_array)):
	#		for y in range(0, len(core_array[0])):
	#			core = core_array[x][y]
	#			core.route()

core_array = []
size = 16
for y in range(0, size):
	cores = []
	east_line = None
	west_line = None
	for x in range(0, size):
		south_line = None if y == size - 1 else Line()
		north_line = None if y == 0 else core_array[y - 1][x].lines[3]
		east_line = Line() if x < size - 1 else None
		cores.append(Core(north_line, east_line, west_line, south_line))
		west_line = east_line
	core_array.append(cores)

for x in range(0, size - 1):
	for y in range(0, size - 1):
		# all lines now "know" connected cores
		core_array[x][y].lines[1].connect(core_array[x][y], core_array[x + 1][y])
		core_array[x][y].lines[3].connect(core_array[x][y], core_array[x][y + 1])

 # These packets intersect at core 1, 1 and neither gets delayed because their routing pipelines do not overlap
core_array[0][1].send_buffer.append(Packet(0, -5))
core_array[1][0].send_buffer.append(Packet(4, -1))

 # Only one of these packets can be sent east first
core_array[0][0].send_buffer.append(Packet(4, -1))
core_array[0][0].send_buffer.append(Packet(4, -1))

 # Only one of these packets can be sent west first
core_array[4][4].send_buffer.append(Packet(-2, -2))
core_array[4][4].send_buffer.append(Packet(-1, -2))

 # These packets meet at an intermediate core but do not conflict because their routing pipelines do not overlap
core_array[2][10].send_buffer.append(Packet(0, -5))
core_array[4][10].send_buffer.append(Packet(0, 3))

 # These packets meet at an intermediate core but do experience a merge delay
core_array[10][9].send_buffer.append(Packet(1, -5))
core_array[9][10].send_buffer.append(Packet(0, -5))

 # This packet attempts to route off the edge of the grid and is destroyed
core_array[15][14].send_buffer.append(Packet(5, -5))

simulate(core_array, 200)
