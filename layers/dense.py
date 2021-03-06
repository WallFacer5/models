import numpy as np
from layers.base import Layer
from constants import Directions


class Dense(Layer):
    def __init__(self, input_layers, output_shape, activation=None, use_bias=False,
                 weights_initializer=np.random.standard_normal,
                 bias_initializer=np.zeros):
        super().__init__(input_layers, output_shape, use_bias, weights_initializer, bias_initializer)
        self.weights = weights_initializer((self.input_shapes[0], self.output_shape)) / 10
        self.delta = np.zeros((self.input_shapes[0], self.output_shape))
        self.activation = activation
        if use_bias:
            self.weights = np.append(self.weights, [bias_initializer(output_shape)], axis=0) / 10
            self.delta = np.append(self.delta, [np.zeros(output_shape)], axis=0)

    def forward(self):
        if self.use_bias:
            self.cur_inputs[0] = np.append(self.cur_inputs[0], np.ones((len(self.cur_inputs[0]), 1)), axis=1)
        self.cur_outputs = np.matmul(self.cur_inputs[0], self.weights)
        # print('Current input:\n{}'.format(self.cur_inputs[0]))
        # print('Forward values:\n{}'.format(self.cur_outputs))
        # print('Weights:\n{}'.format(self.weights))
        if self.activation:
            self.before_activation = np.copy(self.cur_outputs)
            self.cur_outputs = self.activation(self.cur_outputs, Directions.forward)
            # print('Activated:\n{}'.format(np.array(self.cur_outputs)))
        list(map(lambda ol: ol.set_cur_input(self, self.cur_outputs), self.output_layers.keys()))
        self.clear_cur_inputs_flags()

    def backward(self):
        # todo: filter inputs which are actually no need to go
        # mean_inputs = np.array([np.mean(self.cur_inputs[0], axis=0)])
        self.delta = np.sum(self.cur_deltas, axis=0)
        if self.activation:
            # print('Backward gradients:\n{}'.format(np.transpose(-self.delta)))
            self.delta = self.activation(self.before_activation, Directions.backward, self.delta)
        # print('Current gradients:\n{}'.format(np.transpose(-np.matmul(np.transpose(self.cur_inputs[0]), self.delta))))
        backward_delta = np.matmul(self.delta, np.transpose(self.weights))
        # print('Backward gradients:\n{}'.format(np.transpose(-self.delta)))
        if self.use_bias:
            backward_delta = backward_delta[:, :-1]
        list(map(lambda layer: layer.append_cur_delta(self, backward_delta), self.input_layers))
        self.weights += np.matmul(np.transpose(self.cur_inputs[0]), self.delta)
        self.clear_cur_deltas_flags()
