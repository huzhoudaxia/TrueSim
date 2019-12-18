TrueSim, a TrueNorth Routing Simulator

Please see TrueSim.pdf for background, motivation, and results.

General parameters:
	--n_cores: number of cores in the network
	--workload: type of packet-generating policy
	--topology: type of network to simulate

Available workloads:
	"toy"
		-a small set of packets are statically allocated at timestep 0 and allowed to propagate throughout the network
	"random"
		-neurons fire at random with the specified probability dynamically through time
		-unique parameters:
			--probability: probability of a given neuron's firing
			--distance: average distance traveled by a packet
	"faithful"
		-a pseudo spiking neural network is constructed, and packets in the input layer send off spike trains with a specified probability. Spike trains may initiate a downstream neuron's firing.
		-unique parameters:
			--probability: probability of an input neuron's initiation of a spike train
			--n_neurons: number of neurons in the network
			--n_layers: number of layers in the network

Available topologies:
	"mesh"
		-the default 2D mesh network that is included in the real chip
	"3Dmesh"
		-a 3D mesh network