'''	Charles R. Brunstad
	Initial Final Project Hacking
	10/28/19

	The aim of this initial effort was to model a functional piece of the TrueNorth
	chip so as to 1) become more familiar with the architecture, 2) dive into
	the details of modeling such a complex piece of technology from scratch, and 3)
	begin to study the movement of data throughout the chip (1). In particular, the
	"Forward West" part of each core's router was successfully represented
	Pythonically in terms of individual components. Said components are thought of
	as existing in one of two states: 1) performing some operation on a packet
	of data or 2) not performing some operation on a packet of data. Packets are
	propagated through the connected components in discrete intervals. Congestion
	has been cursorily implemented at this time, and future efforts may fully
	address this complicated issue.

	It was seen that a rather large amount of time was required to model even this
	small portion of the chip--this initial effort has perhaps demonstrated that a
	slightly higher-level approach may be warranted in the future.

	Unfortunately, I received feedback for my proposal after starting work on this
	simulator, but at any rate I figured it would serve as a great jumping-off point.
	I'd love to talk with you about the different ways in which I could build upon
	TrueNorth, whether by improving upon the management of interchip
	communications--or something else entirely. Could you by any chance elaborate on
	what you meant when you wrote that it might be worthwhile to explore "varying the
	repertoire of operations that the cores can perform"?

	(1) Akopyan et al.: TrueNorth: Design and Tool Flow of a 65mW 1 Million Neuron
	Programmable Neurosynaptic Chip. IEEE Transactions on Computer-Aided Design
	of Integrated Circuits and Systems, 34 (10), 2015.
'''

import queue

class Packet:
	def __init__(self, value, dx, dy):
		self.value = value
		self.dx = dx
		self.dy = dy
		self.hops = 0	# metrics
		self.gate_delays = 0	# metrics

class ForwardWest:

	def __init__(self, local_source_component, east_source_component):
		self.local_source_component = local_source_component
		self.east_source_component = east_source_component
		self.merge_in = Merger(local_source_component.line_out, east_source_component.line_out)
		self.buffer = Buffer(self.merge_in.line_out)
		self.comparator_x = Comparator(self.buffer.line_out, 'dx', 'zero')
		self.adder = ArithmeticUnit(self.comparator_x.false_out, 'dx', 'increment')
		self.comparator_y = Comparator(self.comparator_x.true_out, 'dy', 'negative')
		self.all_components = {self.local_source_component, self.east_source_component, self.merge_in, self.buffer, self.comparator_x, self.adder, self.comparator_y}

	def outputs(self):
		return [self.adder.line_out, self.comparator_y.true_out, self.comparator_y.false_out]
		#		West 			 	 South						 North

	def direction(self, output):
		self.names = {self.adder.line_out: "west", self.comparator_y.true_out: "south", self.comparator_y.false_out: "north"}
		return self.names[output]

class Component:
	# Useful for dummy components
	def __init__(self):
		self.line_in = Line(None)
		self.line_out = Line(self)
		self.backlog = queue.Queue()

	def stall(self, packet):
		self.backlog.put(packet)

	# To be called in actual simulation
	def safe_execute(self):
		if self.backlog.empty():
			if self.line_in.packet:
				self.execute(self.line_in.packet)
				self.line_in.delete_packet()
		else:
			self.backlog.put(self.line_in.packet)
			self.execute(self.backlog.get())

	def execute(self, packet):
		pass

class Buffer(Component):
	def __init__(self, line_in):
		self.line_in = line_in
		self.line_out = Line(self)
		self.backlog = queue.Queue()

	def execute(self, packet):
		self.line_out.inject(packet)

class Comparator(Component):
	def __init__(self, line_in, direction, kind):
		self.line_in = line_in
		self.true_out = Line(self)
		self.false_out = Line(self)
		self.direction = direction
		self.kind = kind
		self.line_out = None
		self.backlog = queue.Queue()

	def execute(self, packet):
		if packet:
			if self.kind == 'zero':
				if self.direction == 'dx':
					if packet.dx == 0:
						self.true_out.inject(packet)
					else:
						self.false_out.inject(packet)
				else:
					if packet.dy == 0:
						self.true_out.inject(packet)
					else:
						self.false_out.inject(packet)
			else:
				if self.direction == 'dx':
					if packet.dx < 0:
						self.true_out.inject(packet)
					else:
						self.false_out.inject(packet)
				else:
					if packet.dy < 0:
						self.true_out.inject(packet)
					else:
						self.false_out.inject(packet)

class ArithmeticUnit(Component):
	def __init__(self, line_in, direction, kind):
		self.line_in = line_in
		self.line_out = Line(self)
		self.direction = direction
		self.kind = kind
		self.backlog = queue.Queue()

	def execute(self, packet):
		if packet:
			if self.direction == 'dx':
				packet.dx += 1 if self.kind == 'increment' else -1
			else:
				packet.dy += 1 if self.kind == 'increment' else -1
			self.line_out.inject(packet)

class Merger(Component):
	def __init__(self, line_in_1, line_in_2):
		self.line_in_1 = line_in_1
		self.line_in_2 = line_in_2
		self.line_out = Line(self)
		self.line_in = None
		self.backlog = queue.Queue()

	# Overridden because mergers take two inputs
	def safe_execute(self):
		if self.backlog.empty():
			if self.line_in_1.packet:
				self.execute(self.line_in_1.packet)
				self.line_in_1.delete_packet()
			if self.line_in_2.packet:
				self.execute(self.line_in_2.packet)
				self.line_in_2.delete_packet()
		else:
			if self.line_in_1.packet:
				self.backlog.put(self.line_in_1.packet)
			if self.line_in_2.packet:
				self.backlog.put(self.line_in_2.packet)
			self.execute(self.backlog.get())	# Assuming high-throughput
			self.execute(self.backlog.get())

	def execute(self, packet):
		self.line_out.inject(packet)

class Line:
	def __init__(self, component_in):
		self.component_in = component_in
		self.packet = None

	def inject(self, packet):
		if packet and self.packet:
			self.component_in.stall(packet)
		else:
			self.packet = packet

	def delete_packet(self):
		self.packet = None

def next_config(model):
	for component in model.all_components:
		component.safe_execute()

def simulate(model):
	outputs = model.outputs()
	fin = False
	while not fin:
		next_config(model)
		for x in range (0, len(model.outputs())):
			if outputs[x].packet is not None:
				print("Packet has arrived and is destined for rerouting due " + model.direction(outputs[x]))
				fin = True
				break

# Test 1: still heading West! (Authors prioritized east/west movement over north/south)
component_1 = Component()
component_2 = Component()
packet = Packet("Test", -3, -5)
component_1.line_out.inject(packet)
fw = ForwardWest(component_1, component_2)
simulate(fw)

# Test 2: still heading West!
packet = Packet("Test", -3, 5)
component_1.line_out.inject(packet)
fw = ForwardWest(component_1, component_2)
simulate(fw)

# Test 3: done moving laterally, now have to go North
packet = Packet("Test", 0, 5)
component_1.line_out.inject(packet)
fw = ForwardWest(component_1, component_2)
simulate(fw)

#Test 4: done moving laterally, now have to go South
packet = Packet("Test", 0, -5)
component_1.line_out.inject(packet)
fw = ForwardWest(component_1, component_2)
simulate(fw)

