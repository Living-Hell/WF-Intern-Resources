# -*- coding: utf-8 -*-
"""BehaviouralBiometrics.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1DKyX-U3K33NQ9PJadR0zw_W2JviXmqNH
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras import layers, models

# Load the data
data = pd.read_csv('key_press_data.csv')

data.head()

data.tail()

# Preprocess the data
def preprocess_data(data, scaler=None, template_columns=None):
    # Convert key column to string
    data['Key'] = data['Key'].astype(str)

    # One-hot encode the 'Key' column
    data = pd.get_dummies(data, columns=['Key'])

    # Align with template columns if provided
    if template_columns is not None:
        for col in template_columns:
            if col not in data.columns:
                data[col] = 0
        data = data[template_columns]
    else:
        template_columns = data.columns.tolist()

    # Fill any NaN values with 0
    data.fillna(0, inplace=True)

    # Normalize numerical columns
    if scaler is None:
        scaler = StandardScaler()
        data[['Duration', 'Time Between Keys', 'Typing Speed (KPS)', 'Backspace Count', 'Typing Session Duration']] = scaler.fit_transform(
            data[['Duration', 'Time Between Keys', 'Typing Speed (KPS)', 'Backspace Count', 'Typing Session Duration']]
        )
    else:
        data[['Duration', 'Time Between Keys', 'Typing Speed (KPS)', 'Backspace Count', 'Typing Session Duration']] = scaler.transform(
            data[['Duration', 'Time Between Keys', 'Typing Speed (KPS)', 'Backspace Count', 'Typing Session Duration']]
        )

    return data, scaler, template_columns

preprocessed_data, scaler, template_columns = preprocess_data(data)

preprocessed_data.head()

template_columns

# Ensure all columns are numeric
assert preprocessed_data.applymap(np.isreal).all().all()

preprocessed_data.head()

# Split the data into training and test sets
X = preprocessed_data.drop(columns=['User ID'])
y = preprocessed_data['User ID']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Ensure there are no infinite values
X_train.replace([np.inf, -np.inf], np.nan, inplace=True)
X_test.replace([np.inf, -np.inf], np.nan, inplace=True)
X_train.fillna(0, inplace=True)
X_test.fillna(0, inplace=True)

# Convert to numpy arrays
X_train = X_train.to_numpy()
X_test = X_test.to_numpy()

# Ensure the data types are float32
X_train = X_train.astype(np.float32)
X_test = X_test.astype(np.float32)

# Build the autoencoder model
input_dim = X_train.shape[1]
encoding_dim = 32  # Size of the encoding layer

autoencoder = models.Sequential([
    layers.InputLayer(input_shape=(input_dim,)),
    layers.Dense(encoding_dim, activation='relu'),
    layers.Dense(input_dim, activation='sigmoid')
])

autoencoder.compile(optimizer='adam', loss='mse')

autoencoder.add(tf.keras.layers.Dense(256, input_shape=(X_train.shape[1],), activation='sigmoid'))

# Train the autoencoder
autoencoder.fit(X_train, X_train, epochs=50, batch_size=32, validation_data=(X_test, X_test))

# Evaluate the model
reconstructions = autoencoder.predict(X_test)
reconstruction_errors = np.mean(np.square(reconstructions - X_test), axis=1)

# Set a threshold for anomaly detection
threshold = np.mean(reconstruction_errors) + 2 * np.std(reconstruction_errors)

def is_anomaly(new_data, autoencoder, threshold, scaler, template_columns):
    # Preprocess the new data with the same template columns and scaler
    new_data, _, _ = preprocess_data(new_data, scaler, template_columns)

    # Ensure new_data columns match template_columns
    for col in template_columns:
        if col not in new_data.columns:
            new_data[col] = 0

    # Ensure the order of columns matches template_columns
    new_data = new_data[template_columns]

    print("new_data.head()", new_data.head())
    print("New data shape before reshape:", new_data.shape)

    # Convert to numpy array and ensure the data type is float32
    new_data = new_data.to_numpy().astype(np.float32)

    # Reshape the new data to match the expected input shape
    new_data = new_data[:, :autoencoder.input_shape[1]]  # Ensure correct number of features
    new_data = new_data.reshape(-1, autoencoder.input_shape[1])  # Reshape to match the model input shape

    # Check shapes after reshape
    print("New data shape after reshape:", new_data.shape)

    # Predict using the autoencoder
    reconstructions = autoencoder.predict(new_data)
    reconstruction_errors = np.mean(np.square(reconstructions - new_data), axis=1)

    # Check if the reconstruction error exceeds the threshold
    return reconstruction_errors > threshold

# Example usage
new_data = pd.read_csv('new_key_press_data.csv')
anomalies = is_anomaly(new_data, autoencoder, threshold, scaler, template_columns)
print("Anomalies detected:", np.sum(anomalies))

