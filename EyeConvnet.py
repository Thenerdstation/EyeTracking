import tensorflow as tf


slim = tf.contrib.slim


class EyeConvnet():
  def __init__(self, is_training, face_tensor, 
      left_eye_tensor, right_eye_tensor):
    """Eye Tracking Convolutional Network implementation.
    Args:
      is_training: Boolean. Whether network is currently training.
      face_tensor: 4D Tensor. Photo of the cropped face.
      left_eye_tensor: 4D Tensor. Photo of cropped left eye.
      right_eye_tensor: 4D Tensor. Photo of cropped right eye.
    """
    # Set the variables.
    self.is_training= is_training
    self.face_tensor = face_tensor
    self.left_eye_tensor = left_eye_tensor
    self.right_eye_tensor = right_eye_tensor
    # We make a template so that the left and right branches can
    # share weights. 
    eye_branch_template = tf.make_template("eye_branch", 
                                           self.make_eye_branch_no_pooling)
    with tf.variable_scope("face_convnet"):
      face_conv = self.make_face_branch(self.face_tensor)
    with tf.variable_scope("left_eye_convnet"):
      left_eye_conv = eye_branch_template(self.left_eye_tensor)
    with tf.variable_scope("right_eye_convnet"):
      right_eye_conv = eye_branch_template(self.right_eye_tensor)
    left_flat = slim.flatten(left_eye_conv)
    right_flat = slim.flatten(right_eye_conv)
    face_flat = slim.flatten(face_conv)
    # Now start doing the fully connected layers.
    with slim.arg_scope([slim.fully_connected],
                        weights_regularizer=slim.l2_regularizer(0.001),
                        normalizer_fn=slim.batch_norm,
                        normalizer_params={'is_training': self.is_training}):
      with slim.arg_scope([slim.dropout],
                          keep_prob=0.5,
                          is_training=self.is_training):
        left_fc = slim.dropout(
            slim.fully_connected(left_flat, 64, scope='left_fc'))
        right_fc = slim.dropout(
            slim.fully_connected(right_flat, 64, scope='right_fc'))
        face_fc = slim.dropout(
            slim.fully_connected(face_flat, 128, scope='face_fc'))
        eye_concat = tf.concat([left_fc, right_fc], 1)
        eye_fc = slim.dropout(
            slim.fully_connected(eye_concat, 128, scope='eye_fc'))
        all_fc1 = tf.concat([face_fc, eye_fc], 1)
        all_fc2 = slim.dropout(
            slim.fully_connected(all_fc1, 128, scope='all_fc2'))
        # No activation fn for prediction (as prediction can have negative vals).
        self.prediction = slim.fully_connected(
            all_fc2, 2, activation_fn=None, scope='prediction')
      
  def make_face_branch(self, image_input):
    with slim.arg_scope([slim.conv2d], 
                        weights_regularizer=slim.l2_regularizer(0.001),
                        normalizer_fn=slim.batch_norm,
                        normalizer_params={'is_training': self.is_training}):
      net = slim.conv2d(image_input, 32, [11, 11], scope="conv1_11x11")
      net = slim.conv2d(image_input, 64, [5, 5], scope="conv2_5x5")
      net = slim.max_pool2d(net, [2, 2], scope='pool1')
      net = slim.conv2d(image_input, 64, [5, 5], scope="conv3_5x5")
      net = slim.conv2d(image_input, 128, [3, 3], scope="conv4_3x3")
      net = slim.max_pool2d(net, [2, 2], scope='pool2')
      net = slim.conv2d(image_input, 128, [3, 3], scope="conv5_3x3")
      return net
  
  def make_eye_branch(self, image_input):
    raise NotImplemented("We are experimenting first with no pooling")

  def make_eye_branch_no_pooling(self, image_input):
    #TODO(Chase): Test the 'is_training' stuff'.
    with slim.arg_scope([slim.conv2d], 
                        weights_regularizer=slim.l2_regularizer(0.001),
                        normalizer_fn=slim.batch_norm,
                        normalizer_params={'is_training': self.is_training}):
      net = slim.conv2d(image_input, 64, [5, 5], scope="conv1_5x5")
      net = slim.conv2d(image_input, 64, [5, 5], scope="conv2_5x5")
      net = slim.conv2d(image_input, 64, [3, 3], scope="conv3_3x3")
      net = slim.conv2d(image_input, 64, [3, 3], scope="conv4_3x3")
      return net
