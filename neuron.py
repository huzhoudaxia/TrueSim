''' Charles R Brunstad
	Project Hacking: Neuron Simulation
	11/15/19

	In the second part of this week's update, an initial attempt was made at
	simulating the behavior of neurons, which are to be mapped to the various
	TrueNorth cores.

	The plan is to train a spiking neural network capable of identify handwritten
	digits, as this workload will not be too taxing for the computational
	resources available to conduct simulation, as applied both to routing and
	training.

	In this update, neurons are instantiated at the head of the net--that is,
	via the codify_pixels method, they are able to translate data from the
	2D spatial domain to the frequency domain. Sixteen neurons are distributed
	across the training data so as to capture groups of 81 pixels each
	(two pixels of overlap on every border).

	The spiking frequency of immediately connected neurons is determined by
	summing across each of the zones. Image are normalized before conversion
	to the frequency domain.

	Data is pulled from the MNIST dataset via the python-mnist package.
'''

import numpy as np
from mnist import MNIST

LEAK = 0.1

class Neuron:
	def __init__(self, threshold, parent, child):
		self.parents = parent
		self.child = child
		self.membrane_potential = 0
		self.threshold = threshold

	def leak(self):
		self.membrane_potential -= LEAK

	def stimulate(self, weight):
		self.membrane_potential += weight

	def codify_pixels(self, arr):
		intensity = 0
		for x in range(0, len(arr)):
			for y in range(0, len(arr[0])):
				intensity += arr[x][y]
		intensity *= 1000
		return intensity


data = MNIST('./dataset')

x_train, y_train = data.load_training()
x_test, y_test = data.load_testing()


x_train = x_train / np.linalg.norm(x_train)

y_train = np.asarray(y_train).astype(np.int32)
x_test = np.asarray(x_test).astype(np.float32)
y_test = np.asarray(y_test).astype(np.int32)

five = np.reshape(x_train[0], (28, 28))
#print(five)

neurons = []
frequencies = []
for x in range(0, 4):
	neurons.append([])
	frequencies.append([])
	for y in range(0, 4):
		neurons[x].append(Neuron(0, None, None))
		min_x = max(0, (x * 7) - 1)
		max_x = min(28, ((x + 1) * 7) + 1)
		min_y = max(0, (y * 7) - 1)
		max_y = min(28, ((y + 1) * 7) + 1)
		frequencies[x].append(neurons[x][y].codify_pixels(five[min_x:max_x,min_y:max_y]))
for row in frequencies:
	print(row)