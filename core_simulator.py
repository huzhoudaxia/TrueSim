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

	def __init__(self, parent, dx, dy):
		self.dx = dx
		self.dy = dy
		self.hops = 0	# metrics
		self.delays = 0	# metrics
		self.routing_delay = 0
		self.name = Packet.id
		self.parent = parent
		self.directionality = self.determine_directionality()
		self.ready_to_send = False
		Packet.id += 1

	def determine_directionality(self):
		directionality = "southbound" if self.dy < 0 else "northbound"
		directionality = "eastbound" if self.dx > 0 else directionality
		directionality = "westbound" if self.dx < 0 else directionality
		return directionality

class Hardware:
	def __init__(self):
		self.default_routing_delay = 0	# default to no processing time

class Core(Hardware):
	id = 1

	def __init__(self, north_line, east_line, west_line, south_line):
		self.lines = [north_line, east_line, west_line, south_line]
		self.default_routing_delay = 2 # overhead of bundling and unbundling: page 1547
		self.send_buffer = deque()	# used if cannot inject a packet to a transmission line
		self.wait_buffer = deque()	# used to stall so that default routing delay ticks to 0
		self.name = Core.id
		self.packet_out_buffer = [None, None, None, None]
		self.merge_delay = 2
		self.forward_north_merge = None
		self.forward_east_merge = None
		self.forward_south_merge = None
		self.forward_west_merge = None
		Core.id += 1

	def inject(self, packet):
		packet.routing_delay = self.default_routing_delay
		packet.parent = self
		self.wait_buffer.append(packet)

	def route(self):
		'''	Prepare a packet for sendoff, either taken directly from the send buffer, or taken
			from the wait buffer (provided nothing's been queued in the send buffer)
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
					print("Packet " + str(packet.name) + " is at core " + str(self.name) + " and must travel " + str(packet.dx) + " cores in the x and " + str(packet.dy) + " cores in the y")
					blocked_packet = self.forward(packet)
					if blocked_packet:
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
					packet.directionality = 'east-north'
				else:
					packet.directionality = 'east-south'
			else:
				packet.routing_delay = 0	# unsuccessful routes can be immediately reattempted
		elif packet.directionality == 'westbound':
			if self.forward_west_merge == None:
				self.forward_west_merge = packet
				if packet.dx != 0:
					packet.directionality = 'west-exit'
				elif packet.dy > 0:
					packet.directionality = 'west-north'
				else:
					packet.directionality = 'west-south'
			else:
				packet.routing_delay = 0
		elif "south" in packet.directionality:	# accept both southbound packets and packets turning the corner
			if self.forward_south_merge == None:
				self.forward_south_merge = packet
				packet.directionality = 'south-exit'
			else:
				packet.routing_delay = 0
		elif "north" in packet.directionality:	# accept both northbound packets and packets turning the corner
			if self.forward_north_merge == None:
				self.forward_north_merge = packet
				packet.directionality = 'north-exit'
			else:
				packet.routing_delay = 2	# overhead of exiting a core: page 1547
		return (packet, is_outbound)

	def clear_merges(self):
		self.forward_north_merge = None
		self.forward_east_merge = None
		self.forward_south_merge = None
		self.forward_west_merge = None


	def send_out(self):
		for x in range(0, 4):
			if self.lines[x] and self.packet_out_buffer[x]:
				blocked_packet = self.lines[x].inject(self.packet_out_buffer[x])
				if blocked_packet == None:	# only remove packet if it was successfully forwarded
					self.packet_out_buffer[x] = None

	def forward(self, packet):
		''' Adds packets to the appropriate directional output if possible
			Returns packets that it cannot route at the present time
		'''
		if packet.dx > 0:	# send east
			if not self.lines[1]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if not self.lines[1].packet and not self.packet_out_buffer[1]:
				self.packet_out_buffer[1] = packet
				return None
		elif packet.dx < 0:	# send west
			if not self.lines[2]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if not self.lines[2].packet and not self.packet_out_buffer[2]:
				self.packet_out_buffer[2] = packet
				return None
		elif packet.dy > 0:	# send north
			if not self.lines[0]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if not self.lines[0].packet and not self.packet_out_buffer[0]:
				self.packet_out_buffer[0] = packet
				return None
		elif packet.dy < 0: # send south
			if not self.lines[3]:
				print("Packet " + str(packet.name) + " was lost")
				packet.parent = None
				return None 	# destroy packets that attempt to go off the edge
			if not self.lines[3].packet and not self.packet_out_buffer[3]:
				self.packet_out_buffer[3] = packet
				return None
		else:
			# Destroy packet
			print("Packet " + str(packet.name) + " has reached its destination")
			packet.parent = None
			return None
		return packet

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
		if self.packet == None:
			self.packet = packet
			packet.parent = self
			self.packet.routing_delay = self.default_routing_delay
			return None
		else:
			return packet

	def connect(self, terminus_1, terminus_2):
		self.component_1 = terminus_1
		self.component_2 = terminus_2

	def dissassociate(self):
		self.packet = None

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
	for t in range(0, timesteps):
		print(t)
		for packet in packets:
			if isinstance(packet.parent, Line):
				packet.routing_delay = max(0, packet.routing_delay - 1)
		to_visit = []
		for packet in packets:
			if isinstance(packet.parent, Line) and packet.routing_delay == 0:
				packet.parent.dissassociate()
				if packet.dx > 0 and packet.parent.component_2:
					packet.dx -= 1
					packet.directionality = 'eastbound'
					packet.parent.component_2.inject(packet)
				elif packet.dx < 0 and packet.parent.component_1:
					packet.dx += 1
					packet.directionality = 'westbound'
					packet.parent.component_1.inject(packet)
				elif packet.dy > 0 and packet.parent.component_1:
					packet.dy -= 1
					packet.directionality = 'northbound'
					packet.parent.component_1.inject(packet)
				elif packet.dy < 0 and packet.parent.component_2:
					packet.dy += 1
					packet.directionality = 'southbound'
					packet.parent.component_2.inject(packet)
			if isinstance(packet.parent, Core) and packet.parent not in to_visit:
				to_visit.append(packet.parent)
		for core in to_visit:
			core.route()
		random.shuffle(to_visit)
		for core in to_visit:
			core.send_out()


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
		core_array[x][y].lines[1].connect(core_array[x][y], core_array[x][y + 1]) # east --> next column over
		core_array[x][y].lines[3].connect(core_array[x][y], core_array[x + 1][y]) # south --> next row over

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

 # These packets meet at an intermediate core but do experience a merge delay
packets.append(Packet(core_array[10][9], 1, -5))
packets.append(Packet(core_array[9][10], 0, -5))

 # This packet travels off-grid and is lost
packets.append(Packet(core_array[0][10], 0, 5))

for packet in packets:
	packet.parent.inject(packet)

simulate(packets, 90)
