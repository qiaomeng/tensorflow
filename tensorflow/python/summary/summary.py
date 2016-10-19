# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
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

"""## Generation of summaries.

### Summary Ops
@@tensor_summary
@@scalar
@@histogram
@@audio
@@image
@@merge
@@merge_all

## Utilities
@@get_summary_description

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import six

from google.protobuf import json_format as _json_format
from tensorflow.core.framework import summary_pb2 as _summary_pb2
from tensorflow.python.framework import dtypes as _dtypes
from tensorflow.python.framework import ops as _ops
from tensorflow.python.framework import tensor_shape as _tensor_shape
from tensorflow.python.framework.dtypes import as_dtype as _as_dtype
from tensorflow.python.ops import gen_logging_ops as _gen_logging_ops
# exports tensor_summary
from tensorflow.python.ops.summary_ops import tensor_summary
from tensorflow.python.util.all_util import remove_undocumented
from tensorflow.python.util import compat as _compat


def _collect(val, collections, default_collections):
  if collections is None:
    collections = default_collections
  for key in collections:
    _ops.add_to_collection(key, val)


def scalar(name, tensor, summary_description=None, collections=None):
  """Outputs a `Summary` protocol buffer containing a single scalar value.

  The generated Summary has a Tensor.proto containing the input Tensor.

  Args:
    name: A name for the generated node. Will also serve as the series name in
      TensorBoard.
    tensor: A tensor containing a single floating point or integer value.
    summary_description: Optional summary_description_pb2.SummaryDescription
    collections: Optional list of graph collections keys. The new summary op is
      added to these collections. Defaults to `[GraphKeys.SUMMARIES]`.

  Returns:
    A scalar `Tensor` of type `string`. Which contains a `Summary` protobuf.

  Raises:
    ValueError: If tensor has the wrong shape or type.
  """
  dtype = _as_dtype(tensor.dtype)
  if dtype.is_quantized or not (dtype.is_integer or dtype.is_floating):
    raise ValueError("Can't create scalar summary for type %s." % dtype)

  shape = tensor.get_shape()
  if not shape.is_compatible_with(_tensor_shape.scalar()):
    raise ValueError("Can't create scalar summary for shape %s." % shape)

  if summary_description is None:
    summary_description = _summary_pb2.SummaryDescription()
  summary_description.type_hint = 'scalar'

  return tensor_summary(name, tensor, summary_description, collections)


def image(name, tensor, max_outputs=3, collections=None):
  """Outputs a `Summary` protocol buffer with images.

  The summary has up to `max_images` summary values containing images. The
  images are built from `tensor` which must be 4-D with shape `[batch_size,
  height, width, channels]` and where `channels` can be:

  *  1: `tensor` is interpreted as Grayscale.
  *  3: `tensor` is interpreted as RGB.
  *  4: `tensor` is interpreted as RGBA.

  The images have the same number of channels as the input tensor. For float
  input, the values are normalized one image at a time to fit in the range
  `[0, 255]`.  `uint8` values are unchanged.  The op uses two different
  normalization algorithms:

  *  If the input values are all positive, they are rescaled so the largest one
     is 255.

  *  If any input value is negative, the values are shifted so input value 0.0
     is at 127.  They are then rescaled so that either the smallest value is 0,
     or the largest one is 255.

  The `tag` in the outputted Summary.Value protobufs is generated based on the
  name, with a suffix depending on the max_outputs setting:

  *  If `max_outputs` is 1, the summary value tag is '*name*/image'.
  *  If `max_outputs` is greater than 1, the summary value tags are
     generated sequentially as '*name*/image/0', '*name*/image/1', etc.

  Args:
    name: A name for the generated node. Will also serve as a series name in
      TensorBoard.
    tensor: A 4-D `uint8` or `float32` `Tensor` of shape `[batch_size, height,
      width, channels]` where `channels` is 1, 3, or 4.
    max_outputs: Max number of batch elements to generate images for.
    collections: Optional list of ops.GraphKeys.  The collections to add the
      summary to.  Defaults to [_ops.GraphKeys.SUMMARIES]

  Returns:
    A scalar `Tensor` of type `string`. The serialized `Summary` protocol
    buffer.
  """
  with _ops.name_scope(name, None, [tensor]) as scope:
    # pylint: disable=protected-access
    val = _gen_logging_ops._image_summary(
        tag=scope.rstrip('/'),
        tensor=tensor,
        max_images=max_outputs,
        name=scope)
    _collect(val, collections, [_ops.GraphKeys.SUMMARIES])
  return val


def histogram(name, values, collections=None):
  # pylint: disable=line-too-long
  """Outputs a `Summary` protocol buffer with a histogram.

  The generated
  [`Summary`](https://www.tensorflow.org/code/tensorflow/core/framework/summary.proto)
  has one summary value containing a histogram for `values`.

  This op reports an `InvalidArgument` error if any value is not finite.

  Args:
    name: A name for the generated node. Will also serve as a series name in
      TensorBoard.
    values: A real numeric `Tensor`. Any shape. Values to use to
      build the histogram.
    collections: Optional list of graph collections keys. The new summary op is
      added to these collections. Defaults to `[GraphKeys.SUMMARIES]`.

  Returns:
    A scalar `Tensor` of type `string`. The serialized `Summary` protocol
    buffer.
  """
  # pylint: enable=line-too-long
  with _ops.name_scope(name, 'HistogramSummary', [values]) as scope:
    # pylint: disable=protected-access
    val = _gen_logging_ops._histogram_summary(
        tag=scope.rstrip('/'), values=values, name=scope)
    _collect(val, collections, [_ops.GraphKeys.SUMMARIES])
  return val


def audio(name, tensor, sample_rate, max_outputs=3, collections=None):
  # pylint: disable=line-too-long
  """Outputs a `Summary` protocol buffer with audio.

  The summary has up to `max_outputs` summary values containing audio. The
  audio is built from `tensor` which must be 3-D with shape `[batch_size,
  frames, channels]` or 2-D with shape `[batch_size, frames]`. The values are
  assumed to be in the range of `[-1.0, 1.0]` with a sample rate of
  `sample_rate`.

  The `tag` in the outputted Summary.Value protobufs is generated based on the
  name, with a suffix depending on the max_outputs setting:

  *  If `max_outputs` is 1, the summary value tag is '*name*/audio'.
  *  If `max_outputs` is greater than 1, the summary value tags are
     generated sequentially as '*name*/audio/0', '*name*/audio/1', etc

  Args:
    name: A name for the generated node. Will also serve as a series name in
      TensorBoard.
    tensor: A 3-D `float32` `Tensor` of shape `[batch_size, frames, channels]`
      or a 2-D `float32` `Tensor` of shape `[batch_size, frames]`.
    sample_rate: A Scalar `float32` `Tensor` indicating the sample rate of the
      signal in hertz.
    max_outputs: Max number of batch elements to generate audio for.
    collections: Optional list of ops.GraphKeys.  The collections to add the
      summary to.  Defaults to [_ops.GraphKeys.SUMMARIES]

  Returns:
    A scalar `Tensor` of type `string`. The serialized `Summary` protocol
    buffer.
  """
  # pylint: enable=line-too-long
  with _ops.name_scope(name, None, [tensor]) as scope:
    # pylint: disable=protected-access
    sample_rate = _ops.convert_to_tensor(
        sample_rate, dtype=_dtypes.float32, name='sample_rate')
    val = _gen_logging_ops._audio_summary_v2(
        tag=scope.rstrip('/'),
        tensor=tensor,
        max_outputs=max_outputs,
        sample_rate=sample_rate,
        name=scope)
    _collect(val, collections, [_ops.GraphKeys.SUMMARIES])
  return val


def merge(inputs, collections=None, name=None):
  # pylint: disable=line-too-long
  """Merges summaries.

  This op creates a
  [`Summary`](https://www.tensorflow.org/code/tensorflow/core/framework/summary.proto)
  protocol buffer that contains the union of all the values in the input
  summaries.

  When the Op is run, it reports an `InvalidArgument` error if multiple values
  in the summaries to merge use the same tag.

  Args:
    inputs: A list of `string` `Tensor` objects containing serialized `Summary`
      protocol buffers.
    collections: Optional list of graph collections keys. The new summary op is
      added to these collections. Defaults to `[GraphKeys.SUMMARIES]`.
    name: A name for the operation (optional).

  Returns:
    A scalar `Tensor` of type `string`. The serialized `Summary` protocol
    buffer resulting from the merging.
  """
  # pylint: enable=line-too-long
  with _ops.name_scope(name, 'Merge', inputs):
    # pylint: disable=protected-access
    val = _gen_logging_ops._merge_summary(inputs=inputs, name=name)
    _collect(val, collections, [])
  return val


def merge_all(key=_ops.GraphKeys.SUMMARIES):
  """Merges all summaries collected in the default graph.

  Args:
    key: `GraphKey` used to collect the summaries.  Defaults to
      `GraphKeys.SUMMARIES`.

  Returns:
    If no summaries were collected, returns None.  Otherwise returns a scalar
    `Tensor` of type `string` containing the serialized `Summary` protocol
    buffer resulting from the merging.
  """
  summary_ops = _ops.get_collection(key)
  if not summary_ops:
    return None
  else:
    return merge(summary_ops)


def get_summary_description(node_def):
  """Given a TensorSummary node_def, retrieve its SummaryDescription.

  When a Summary op is instantiated, a SummaryDescription of associated
  metadata is stored in its NodeDef. This method retrieves the description.

  Args:
    node_def: the node_def_pb2.NodeDef of a TensorSummary op

  Returns:
    a summary_pb2.SummaryDescription

  Raises:
    ValueError: if the node is not a summary op.
  """

  if node_def.op != 'TensorSummary':
    raise ValueError("Can't get_summary_description on %s" % node_def.op)
  description_str = _compat.as_str_any(node_def.attr['description'].s)
  summary_description = _summary_pb2.SummaryDescription()
  _json_format.Parse(description_str, summary_description)
  return summary_description


remove_undocumented(__name__, [])
