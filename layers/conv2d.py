import numpy as np
from layers.base import Layer
from constants import Directions
from numba import jit


class Conv2d(Layer):
    def __init__(self, input_layers, num_filters, kernel_size=[2, 2], strides=[1, 1], padding=[0, 0], activation=None,
                 use_bias=False, weights_initializer=np.random.standard_normal, bias_initializer=np.zeros):
        super().__init__(input_layers, None, use_bias, weights_initializer, bias_initializer)
        self.num_filters = num_filters
        self.kernel_size = kernel_size
        self.strides = strides
        self.padding = padding
        self.activation = activation
        self.output_shape = [0, 0, 0]
        input_shape = self.input_shapes[0]
        self.output_shape[0] = (input_shape[0] + 2 * padding[0] - kernel_size[0]) // strides[0] + 1
        self.output_shape[1] = (input_shape[1] + 2 * padding[1] - kernel_size[1]) // strides[1] + 1
        self.output_shape[2] = num_filters
        self.filters = weights_initializer([num_filters] + kernel_size + [input_shape[2]])
        # self.delta = np.zeros([num_filters] + kernel_size + [input_shape[2]])
        if self.use_bias:
            self.biases = bias_initializer(num_filters)

    @staticmethod
    @jit(nopython=True)
    def in_forward(cur_outputs, cur_inputs, output_shape, filters, strides, kernel_size, use_bias, biases):
        for i in range(output_shape[0]):
            for j in range(output_shape[1]):
                for k, f in enumerate(filters):
                    for s in range(cur_inputs[0].shape[0]):
                        cur_value = cur_inputs[0][s, i * strides[0]:i * strides[0] + kernel_size[0],
                                    j * strides[1]:j * strides[1] + kernel_size[1]]
                        cur_outputs[s][i][j][k] = np.sum(cur_value * f)
                        if use_bias:
                            cur_outputs[s][i][j][k] += biases[k]
        return cur_outputs

    def forward(self):
        '''
        self.cur_outputs = np.zeros([self.cur_inputs[0].shape[0]] + self.output_shape)
        for i in range(self.output_shape[0]):
            for j in range(self.output_shape[1]):
                for k, f in enumerate(self.filters):
                    for s in range(self.cur_inputs[0].shape[0]):
                        cur_value = self.cur_inputs[0][s, i * self.strides[0]:i * self.strides[0] + self.kernel_size[0],
                                    j * self.strides[1]:j * self.strides[1] + self.kernel_size[1]]
                        self.cur_outputs[s][i][j][k] = np.sum(cur_value * f)
                        if self.use_bias:
                            self.cur_outputs[s][i][j][k] += self.biases[k]
        if self.activation:
            self.before_activation = np.copy(self.cur_outputs)
            self.cur_outputs = self.activation(self.cur_outputs, Directions.forward)
        '''

        cur_outputs = np.zeros([self.cur_inputs[0].shape[0]] + self.output_shape)
        self.cur_outputs = self.in_forward(cur_outputs, self.cur_inputs, self.output_shape, self.filters, self.strides,
                                           self.kernel_size, self.use_bias, self.biases)
        if self.activation:
            self.before_activation = np.copy(self.cur_outputs)
            self.cur_outputs = self.activation(self.cur_outputs, Directions.forward)
        list(map(lambda ol: ol.set_cur_input(self, self.cur_outputs), self.output_layers.keys()))
        self.clear_cur_inputs_flags()

    @staticmethod
    @jit(nopython=True)
    def in_backward(dx, df, db, cur_inputs, output_shape, filters, strides, kernel_size, use_bias, delta):
        for i in range(output_shape[0]):
            for j in range(output_shape[1]):
                for k, f in enumerate(filters):
                    for s in range(cur_inputs[0].shape[0]):
                        dx[s, i * strides[0]:i * strides[0] + kernel_size[0],
                        j * strides[1]:j * strides[1] + kernel_size[1]] += \
                            f * delta[s, i, j, k]
                        if use_bias:
                            db[k] += delta[s, i, j, k]
                        cur_value = cur_inputs[0][s, i * strides[0]:i * strides[0] + kernel_size[0],
                                    j * strides[1]:j * strides[1] + kernel_size[1]]
                        df[k] += cur_value * delta[s, i, j, k]
        return dx, df, db

    def backward(self):
        '''
        delta = np.sum(self.cur_deltas, axis=0)
        dx = np.zeros(self.cur_inputs[0].shape)
        df = np.zeros_like(self.filters)
        if self.use_bias:
            db = np.zeros_like(self.biases)
        if self.activation:
            delta = self.activation(self.before_activation, Directions.backward, delta)
        for i in range(self.output_shape[0]):
            for j in range(self.output_shape[1]):
                for k, f in enumerate(self.filters):
                    for s in range(self.cur_inputs[0].shape[0]):
                        dx[s, i * self.strides[0]:i * self.strides[0] + self.kernel_size[0],
                        j * self.strides[1]:j * self.strides[1] + self.kernel_size[1]] += \
                            f * delta[s, i, j, k]
                        if self.use_bias:
                            db[k] += np.sum(delta[s, i, j, k])
                        cur_value = self.cur_inputs[0][s, i * self.strides[0]:i * self.strides[0] + self.kernel_size[0],
                                    j * self.strides[1]:j * self.strides[1] + self.kernel_size[1]]
                        df[k] += cur_value * delta[s, i, j, k]
        '''
        dx = np.zeros(self.cur_inputs[0].shape)
        df = np.zeros_like(self.filters)
        if self.use_bias:
            db = np.zeros_like(self.biases)
        delta = np.sum(self.cur_deltas, axis=0)
        if self.activation:
            delta = self.activation(self.before_activation, Directions.backward, delta)
        dx, df, db = self.in_backward(dx, df, db, self.cur_inputs, self.output_shape, self.filters, self.strides,
                                      self.kernel_size, self.use_bias, delta)
        list(map(lambda layer: layer.append_cur_delta(self, dx), self.input_layers))
        self.filters += df
        self.biases += db
        self.clear_cur_deltas_flags()
