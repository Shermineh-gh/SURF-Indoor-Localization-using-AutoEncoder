import pandas as pd
import tensorflow as tf
import numpy as np
from sklearn.preprocessing import scale
from keras.models import Sequential, Model
from keras.layers import Input, Dense, Dropout
from keras.callbacks import TensorBoard



path_train = "./UJIndoorLoc/trainingData.csv"
path_validation = "./UJIndoorLoc/validationData.csv"



#Explicitly pass header=0 to be able to replace existing names 
train_df = pd.read_csv(path_train,header = 0)
train_df = train_df[:19930]
train_AP_strengths = train_df.ix[:,:520] #select first 520 columns

#Scale transforms data to center to the mean and component wise scale to unit variance
train_AP_features = scale(np.asarray(train_AP_strengths))

#The following two objects are actually pandas.core.series.Series objects
building_ids_str = train_df["BUILDINGID"].map(str) #convert all the building ids to strings
building_floors_str = train_df["FLOOR"].map(str) #convert all the building floors to strings

res = building_ids_str + building_floors_str #element wise concatenation of BUILDINGID+FLOOR
train_labels = np.asarray(building_ids_str + building_floors_str)
print('Building ID: \n', building_ids_str)
print('Floor ID: \n', building_floors_str)
print('Res', res)
print('train_labels: \n', train_labels)
#convert labels to categorical variables, dummy_labels has type 'pandas.core.frame.DataFrame'
dummy_labels = pd.get_dummies(train_labels)
print('dummy_lables: \n', dummy_labels)


"""one hot encode the dummy_labels.
this is done because dummy_labels is a dataframe with the labels (BUILDINGID+FLOOR) 
as the column names
"""
train_labels = np.asarray(dummy_labels) #labels is an array of shape 19937 x 13. (there are 13 types of labels)



#generate len(train_AP_features) of floats in between 0 and 1
train_val_split = np.random.rand(len(train_AP_features))
#convert train_val_split to an array of booleans: if elem < 0.7 = true, else: false
train_val_split = train_val_split < 0.90 #should contain ~70% percent true



# We will then split our given training set into training + validation 
train_X = train_AP_features[train_val_split]
train_y = train_labels[train_val_split]
val_X = train_AP_features[~train_val_split]
val_y = train_labels[~train_val_split]



#Turn the given validation set into a testing set
test_df = pd.read_csv(path_validation,header = 0)
test_AP_features = scale(np.asarray(test_df.ix[:,0:520]))
test_labels = np.asarray(test_df["BUILDINGID"].map(str) + test_df["FLOOR"].map(str))
test_labels = np.asarray(pd.get_dummies(test_labels))



nb_epochs = 20
batch_size = 10
input_size = 520
num_classes = 13


# ------------------- AutoEncoder ---------------------- #

input_rss = Input(shape=(input_size, ))
encoded = Dense(256, activation='tanh', use_bias=True)(input_rss)
encoded = Dense(128, activation='tanh', use_bias=True)(encoded)
encoded = Dense(64, activation='tanh', use_bias=True)(encoded)
decoded = Dense(128, input_dim=64, activation='tanh', use_bias=True)(encoded)
decoded = Dense(256, activation='tanh', use_bias=True)(decoded)
decoded = Dense(input_size, activation='tanh', use_bias=True)(decoded)

autoencoder = Model(input_rss, decoded)

encoder = Model(input_rss, encoded)

autoencoder.compile(optimizer='adam', loss='mse')

autoencoder.fit(train_X, train_X, epochs=nb_epochs*4, batch_size=batch_size*25, callbacks=[TensorBoard(log_dir='./graphs/SAE')])

# --------------------- Classifier ------------------------ #

input_code = Input(shape=(64, ))
prediction = Dense(128, input_dim=64, activation='relu', use_bias=True)(input_code)
prediction = Dense(128, activation='relu', use_bias=True)(prediction)
prediction = Dense(num_classes, activation='softmax', use_bias=True)(prediction)

classifier = Model(input_code, prediction)
classifier.compile(optimizer='adam', loss='categorical_crossentropy',metrics=['accuracy'])

classifier.fit(encoder.outputs, train_y, validation_data=(val_X, val_y), epochs=nb_epochs, batch_size=batch_size, callbacks=[TensorBoard(log_dir='./graphs/classifier')])

loss, acc = classifier.evaluate(test_AP_features, test_labels)

print('\n', loss, acc)

