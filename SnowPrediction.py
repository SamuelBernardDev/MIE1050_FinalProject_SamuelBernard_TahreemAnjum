import serial
import time
import numpy as np
import re
import pandas as pd
import math

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder

# Load the dataset
file_path = "snowingData.csv"
snowing_data = pd.read_csv(file_path)

# Prepare the features and labels
X = snowing_data[["Temperature (Celsius)", "Humidity (%)", "Distance (mm)", "Density (kg/mm3)"]]
y = snowing_data["Label"]

# Encode the classes for snow into numbers
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Split the data into training and test
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

# Create a Random Forest classifier
random_forest = RandomForestClassifier(random_state=42)
random_forest.fit(X_train, y_train)

# Predict the test set to evaluate the performance of the model
y_pred = random_forest.predict(X_test)

# Evaluate the classifier
accuracy = accuracy_score(y_test, y_pred)
report = classification_report(y_test, y_pred, target_names=label_encoder.classes_)

# Get the feature importances
feature_importances = random_forest.feature_importances_

# Display the results for classification on test set
print("Accuracy:", accuracy)
print("\nClassification Report:\n", report)

# Display the important features
important_features = pd.DataFrame({
    "Feature": X.columns,
    "Importance": feature_importances
}).sort_values(by="Importance", ascending=False)
important_features.reset_index(drop=True, inplace=True)
print(important_features)



# Initialize serial connections
arduino_com4 = serial.Serial('COM4', 9600)  # COM4 for infrared/load cell Arduino
arduino_com5 = serial.Serial('COM5', 115200)  # COM5 for temperature/humidity ESP32
time.sleep(2)

# Offset values to calibrate the temp/hum sensor and remove impact from plastic plate (thickness and weight)
offsetTemp = -6.25
offsetHum = -19.04
offsetDistance = 141.074
offsetWeight = 10.157


def wait_for_input():
    """Wait for user input to send the start signal."""
    while True:
        user_input = input("Enter 'start' to begin recording or 'exit' to quit: ").strip().lower()
        if user_input == 'start':
            return True  # Send the start signal
        elif user_input == 'exit':
            return False  # Exit the script
        else:
            print("Invalid input. Please enter 'start' or 'exit'.")

# Function to read data from COM4 for weight and distance
def read_from_com4(avg_temp, avg_hum):
    pattern = r"[-+]?\d*\.\d+|\d+"
    speed_of_sound = (331.4 + 0.606*avg_temp+0.0124*avg_hum)*0.001 #mm/micros no longer used due to infrared sensor instead
    if arduino_com4.in_waiting > 0:
        data = arduino_com4.readline().decode('utf-8').strip()
        print(f"COM4 Data: {data}")
        match = re.search(pattern, data)
        if match:
            number_str = match.group()
            value = float(number_str)
            if data.startswith("Distance:"):
                print(value)
                list_sol.append(value)
                print(f"Extracted distance: {value} cm")
            elif data.startswith("Weight:"):
                list_weight.append(value)
                print(f"Extracted weight: {value} g")
        return data
    return None



# Function to read data from COM5 for BME680 temperature and humidity
def read_from_com5():
    pattern = r"[-+]?\d*\.\d+|\d+"
    if arduino_com5.in_waiting > 0:
        data = arduino_com5.readline().decode('utf-8').strip()
        print(f"COM5 Data: {data}")
        match = re.search(pattern, data)
        if match:
            number_str = match.group()
            value = float(number_str)
            if data.startswith("Temp:"):
                new_value = value+offsetTemp
                list_temp.append(new_value)
                print(f"Extracted temperature: {new_value} °C")
            elif data.startswith("Hum:"):
                new_value = value+offsetHum
                list_hum.append(new_value)
                print(f"Extracted humidity: {new_value} %")
        return data
    return None

# Main loop

while True:
    print("Waiting for user input...")
    if wait_for_input():
        # Initialize data lists
        list_temp = []
        list_hum = []

        # Weight and distance
        list_sol, list_weight = [], []
        print("Sending start signal to Arduinos...")
        arduino_com4.write(b"start\n")  # Send the start signal to COM4 Arduino
        arduino_com5.write(b"start\n")  # Send the start signal to COM5 Arduino
        
        # Collect and display data until 'Done' is received
        done_com5 = False
        done_com4=False
        while not done_com5:
            data_com5 = read_from_com5()
            if data_com5 and "Done" in data_com5:
                done_com5 = True
        np_temp, np_hum = np.array(list_temp), np.array(list_hum)
        avg_temp, avg_hum = np.mean(np_temp), np.mean(np_hum)

        while not done_com4:
            data_com4 = read_from_com4(avg_temp, avg_hum)
            if data_com4 and "Done" in data_com4:
                done_com4 = True
        np_distance, np_weight = np.array(list_sol), np.array(list_weight)
        avg_distance, avg_weight = np.mean(np_distance), np.mean(np_weight)
        true_weight = avg_weight-offsetWeight
        
        if offsetDistance-avg_distance<0:
            true_distance=0
            meter_volume=0
            density = 0
        else:
            true_distance=offsetDistance-avg_distance
            volume_plate = math.pi*(46.228**2)*true_distance
            kg_weight, meter_volume = true_weight/1000, volume_plate/1000000000
            if kg_weight/meter_volume<0:
                density=0
            else:
                density = kg_weight/meter_volume
                
        input_to_model = np.array([[avg_temp,avg_hum, avg_distance,density]])

        predicted_label_index = random_forest.predict(input_to_model)[0]
        predicted_label = label_encoder.inverse_transform([predicted_label_index])[0]
        
        # Print the measurements 
        print("distance", avg_distance)
        print("True Accumulation: ", true_distance,"mm")
        print("True weight: ", true_weight)
        print('density', density)
        print("Temperature Data:", np.mean(np_temp))
        print("Humidity Data:", np.mean(np_hum))
        print("")
        print("The Prediction is: ", predicted_label)
        print("The Prediction is: ", predicted_label)
        print("The Prediction is: ", predicted_label)
        print("Data collection completed.")


    else:
        print("Exiting...")
        break
