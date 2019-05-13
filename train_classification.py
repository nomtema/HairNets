# -*- coding: utf-8 -*-
"""
Created on Mon May 13 01:06:38 2019

@author: Gael
"""

import gc
gc.collect()
import os
import tensorflow as tf
import numpy as np
import scipy.io
import sys
sys.path.insert(0, 'lib/')
from GoogleNetwork import GoogLeNet as DNN
from keras.preprocessing.image import img_to_array, load_img

########################### This file is used to train the data


###############              Folder locations
# Specify the location of the hair segment obtained from data augmentation
folder_data_a = ''   
folder_data_b = ''
folder_data_c = ''

###############                Parameters
iterations = 30000
batch_size = 61
number_channels = 3

############       Results to save
loss_hair_type = np.zeros((iterations))


#############            Function to read the training data
# The file dataset_train.txt is read and parsed
def reading_training_data(folder_data, hair_type):
    # y_train = hair type: [p_a, p_b, p_c] softmax
    # X_train: training images nx224x224x3
    # hair_type is either 'a' for type_a, 'b' for type_b and 'c' for type_c
    allimages = os.listdir(folder_data)
    number_images = len(allimages)
    y_train = np.zeros((number_images, 3))
    X_train = np.zeros((number_images, 224, 224, number_channels))
    
    if hair_type == 'a':
        label = np.array([1, 0, 0])
    elif hair_type == 'b':
        label = np.array([0, 1, 0])
    else:
        label = np.array([0, 0, 1])
    
    print('Total images for training for this type', len(allimages))

    for i in len(allimages):
        y_train[i, :, :, :] = label
        img = load_img(folder_data+allimages[i]) # This is a PIL image
        X_train[i, :, :, :] = img_to_array(img)  # this is a Numpy array with shape (3, 224, 224)
    return X_train, y_train

#############            Normalization
    #We normalize the data by substracting the mean and scaling 
def normalization(X_train, y_train):
    # Forcing the pixels as floats
    X_train = X_train.astype('float32')
    MEAN = np.mean(X_train, axis=(0,1,2))  #Calculating the mean for each channel
    X_train = X_train - X_train.mean(axis=(0,1,2),keepdims=1)  # Substracting the mean 
    X_train /= 1.0        # Scaling to [-1, 1]  X_train2 /= 255
    return X_train, MEAN


#We shuffle the data
def shuffle_data(X_train, y_train):
    #Initial order of images
    order = np.arange(len(X_train)) 
    # New order  when shuffling
    np.random.shuffle(order)
    # Shuffle the data
    X_train = X_train[order, :]
    y_train = y_train[order, :]
    return X_train, y_train


#We generate the batch
def generate_batch_input_data(X_train, y_train, batch_size):
    number_batch = len(X_train) // batch_size
    while True:
        for i in range(number_batch):
            X_train_batch = X_train[i*batch_size:(i+1)*batch_size, :]
            y_train_batch = y_train[i*batch_size:(i+1)*batch_size, :]
            yield X_train_batch, y_train_batch
        
        
##############################################################################
##############################################################################
##############################################################################

# Reset the graph
tf.reset_default_graph()

#Placeholder input data: image and hair type
image_data = tf.placeholder(tf.float32, [batch_size, 224, 224, number_channels], name="image_data")
type_true = tf.placeholder(tf.float32, [batch_size, 3],  name="type_true")


# Deep Neural Network
net = DNN({'data': image_data})

#Output of DNN

# First  softmax
type_pred_1 = net.layers['type_1']

# Second  softmax
type_pred_2 = net.layers['type_2']

# Thord  softmax
type_pred_3 = net.layers['type_3']

#Loss function

loss_1 = tf.reduce_mean(-tf.reduce_sum(type_true * tf.log(type_pred_1), reduction_indices=[1]))

loss_2 = tf.reduce_mean(-tf.reduce_sum(type_true * tf.log(type_pred_2), reduction_indices=[1]))

loss_3 = tf.reduce_mean(-tf.reduce_sum(type_true * tf.log(type_pred_3), reduction_indices=[1]))


loss = 0.3*loss_1 + 0.3*loss_2 + loss_3 # weighted sum for auxiliary ouput and main output in googlenet architecture

#Optimizer
opt = tf.train.AdamOptimizer(learning_rate=0.0001, beta1=0.9, beta2=0.999, epsilon=0.00000001, use_locking=False, name='Adam').minimize(loss)

# Initializer variable
init = tf.global_variables_initializer()

#Getting data
print('Reading the data')
X_train_a, y_train_a= reading_training_data(folder_data_a, 'a')
X_train_b, y_train_b= reading_training_data(folder_data_b, 'b')
X_train_c, y_train_c= reading_training_data(folder_data_c, 'c')

X_train = np.append(X_train_a, X_train_b)
y_train = np.append(y_train_a, y_train_b)

X_train = np.append(X_train, X_train_c)
y_train = np.append(y_train, y_train_c)

X_train, MEAN = normalization(X_train)

scipy.io.savemat('Save/MEAN.mat', mdict={'MEAN': MEAN})
print("Shape of y_train ", np.shape(y_train))
print("Shape of X_train ", np.shape(X_train))

# Shuffling and setting the batch
X_train, y_train = shuffle_data(X_train, y_train)
new_batch = generate_batch_input_data(X_train, y_train, batch_size)

saver = tf.train.Saver()

outputFile = "/Save/Hair.ckpt"

gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.9133)
print('Starting training')
with tf.Session(config=tf.ConfigProto(gpu_options=gpu_options)) as sess:
    sess.run(init)
    # Loading the pretrained weights
    net.load('weights/weights_classification.npy', sess)
    for i in range(iterations):
        #Getting the current batch
        print('iteration', i)
        X_train_batch, y_train_batch = next(new_batch)

        feed = {image_data: X_train_batch, type_true: y_train_batch}
    
        sess.run(opt, feed_dict=feed)
        
        loss_hair_type[i] = sess.run(loss, feed_dict=feed) # Only the last layer is considered as the prediction
                
        if i % 1000 == 0:
            saver.save(sess, outputFile)
            scipy.io.savemat('Save/loss_hair_iteration.mat', mdict={'loss_hair_iteration': loss_hair_type})
        if i % 100 == 0:
            print('iteration number ', i)
            print(' ----------------------- loss ', loss_hair_type[i])
    
    saver.save(sess, outputFile)

    
print('end of training') 