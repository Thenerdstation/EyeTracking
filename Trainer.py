from __future__ import print_function


import tensorflow as tf
import EyeConvnet
import numpy as np
from misc import loadmat
import Preprocess
import FastDataset

slim = tf.contrib.slim


class Trainer():

  """Trains and evalualuates the EyeConvnet model"""

  def __init__(self, mat_files, batch_size=32, save_dest=None,
         eval_loop=False):
    """Trainer object.
    Args:
      mat_filess: List of file names to the '.mat' data files.
      batch_size: Batch size to use for training.
      save_dest: Where to save the saved models and tensorboard events.
      eval_loop: Boolean. Determins whether this Trainer is actually an
      evaluator.
    """
    # TODO(Chase): This may not work beyond some large files.
    # We'll test and debug later if that is the case.
    (self.face_tensor,
    self.left_eye_tensor,
    self.right_eye_tensor,
    self.gaze,
    self.pts) = FastDataset.get_eyetracking_tensors(
        mat_files, batch_size, eval_loop)
    tf.summary.histogram("gaze", self.gaze)
    self.gaze_normal = (self.gaze / (1500, 800)) - 1  
    tf.summary.image(
      "face", Preprocess.image_correction(self.face_tensor))
    tf.summary.image(
      "left", Preprocess.image_correction(self.left_eye_tensor))
    tf.summary.image(
      "right", Preprocess.image_correction(self.right_eye_tensor))
    self.save_dest = save_dest
    self.model = EyeConvnet.EyeConvnet(
      not eval_loop,
      self.face_tensor,
      self.left_eye_tensor,
      self.right_eye_tensor,
      self.pts)
    self.opt = tf.train.AdamOptimizer()
    self.loss = tf.losses.mean_squared_error(
      self.gaze_normal, self.model.prediction)
    self.pixels_off = tf.reduce_mean(tf.reduce_mean(tf.abs(
      self.gaze - (self.model.prediction + 1) * (1500, 800))))
    self.train_op = slim.learning.create_train_op(self.loss, self.opt)

  def train(self, training_steps=100000, restore=None):
    """Trains the EyeConvnet Model.
    Args:
      training_steps: Number of training steps. Defaults to 100,000
      restore: Possible checkpoint to restore from. If None, then nothing is
        restored.
    """
    tf.summary.scalar("loss", self.loss)
    tf.summary.scalar("pixel_difference", self.pixels_off)
    # Histogram for all of the variables.
    for var in tf.trainable_variables():
      tf.summary.histogram(var.name, var)
    if restore is not None:
      raise NotImplementedError("Restore is not implemented")
    self.init_op = tf.global_variables_initializer()
    if self.save_dest is not None:
      saver = tf.train.Saver(
        keep_checkpoint_every_n_hours=0.01)  # every 12 minutes.
    else:
      saver = None
    slim.learning.train(
      self.train_op,
      self.save_dest,
      number_of_steps=training_steps,
      init_op=self.init_op,
      saver=saver,
      save_summaries_secs=60,
      save_interval_secs=360)

  def evaluate(self, num_evals=50, eval_secs=30, timeout=None, person=None):
    """ Runs the eval loop
    Args:
      num_evals: How many times to do the eval loop.
      eval_secs: How often to run the eval loop. Default to 1 minute
      timeout: Default to None, only used for unit testing.
      person: Person we are evaling.

    """
    names_to_values, names_to_updates = slim.metrics.aggregate_metric_map({
      "pixel_difference": tf.metrics.mean_absolute_error(
        (self.model.prediction + 1) * (1500, 800), self.gaze)  # Get approximate error
    })
    summary_ops = []
    for metric_name, metric_value in names_to_values.items():
      op = tf.summary.scalar(metric_name, metric_value)
      op = tf.Print(op, [metric_value], metric_name)
    summary_ops.append(op)
    # Force it not to use all of the CPUs.
    config = tf.ConfigProto(
      intra_op_parallelism_threads=16,
      inter_op_parallelism_threads=16)
    slim.evaluation.evaluation_loop(
      '',
      self.save_dest,
      self.save_dest + "/eval",
      num_evals=num_evals,
      eval_interval_secs=eval_secs,
      eval_op=list(names_to_updates.values()),
      summary_op=tf.summary.merge_all(),
      timeout=timeout,
      session_config=config)
