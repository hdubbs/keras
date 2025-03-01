# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests Keras integration with enable_mixed_precision_graph_rewrite()."""

import tensorflow.compat.v2 as tf

import os
from keras.testing_infra import test_combinations
from keras.testing_infra import test_utils
from keras.mixed_precision import loss_scale_optimizer as loss_scale_optimizer_v2
from keras.mixed_precision import policy
from keras.optimizers.optimizer_v2 import gradient_descent as gradient_descent_v2


class MixedPrecisionTest(test_combinations.TestCase):

  IGNORE_PERF_VAR = 'TF_AUTO_MIXED_PRECISION_GRAPH_REWRITE_IGNORE_PERFORMANCE'

  def setUp(self):
    super(MixedPrecisionTest, self).setUp()
    # Enable the tests to be run on pre-Volta GPUs by telling the grappler pass
    # to ignore performance and always transform the graph.
    self._original_ignore_perf_value = os.getenv(self.IGNORE_PERF_VAR)
    os.environ[self.IGNORE_PERF_VAR] = '1'

  def tearDown(self):
    # Set the IGNORE_PERF_VAR variable back to it's original value.
    if self._original_ignore_perf_value is not None:
      os.environ[self.IGNORE_PERF_VAR] = self._original_ignore_perf_value
    else:
      del os.environ[self.IGNORE_PERF_VAR]

    tf.compat.v1.mixed_precision.disable_mixed_precision_graph_rewrite()
    super(MixedPrecisionTest, self).tearDown()

  @test_combinations.generate(
      test_combinations.combine(mode=['graph', 'eager']))
  def test_wrap_optimizer(self):
    opt = gradient_descent_v2.SGD(1.0)
    opt = tf.compat.v1.mixed_precision.enable_mixed_precision_graph_rewrite(opt, 123.)
    self.assertIsInstance(
        opt, loss_scale_optimizer_v2.LossScaleOptimizerV1)
    self.assertEqual(self.evaluate(opt.loss_scale), 123.)

  @test_combinations.generate(
      test_combinations.combine(mode=['graph', 'eager']))
  def test_optimizer_errors(self):
    opt = gradient_descent_v2.SGD(1.0)
    opt = loss_scale_optimizer_v2.LossScaleOptimizerV1(opt, 'dynamic')
    with self.assertRaisesRegex(
        ValueError, '"opt" must not already be an instance of a '
        'LossScaleOptimizer.'):
      tf.compat.v1.mixed_precision.enable_mixed_precision_graph_rewrite(opt)
    self.assertFalse(tf.config.optimizer.get_experimental_options()
                     .get('auto_mixed_precision', False))

  @test_utils.enable_v2_dtype_behavior
  def test_error_if_policy_is_set(self):
    with policy.policy_scope('mixed_float16'):
      with self.assertRaisesRegex(ValueError,
                                  'the global Keras dtype Policy has been set'):
        tf.compat.v1.mixed_precision.enable_mixed_precision_graph_rewrite(
            gradient_descent_v2.SGD(1.0))
    # Test no error is thrown when the policy is currently the default.
    tf.compat.v1.mixed_precision.enable_mixed_precision_graph_rewrite(
        gradient_descent_v2.SGD(1.0))
    # Test no error is thrown when the policy is a non-mixed policy.
    with policy.policy_scope('float64'):
      tf.compat.v1.mixed_precision.enable_mixed_precision_graph_rewrite(
          gradient_descent_v2.SGD(1.0))


if __name__ == '__main__':
  tf.test.main()
