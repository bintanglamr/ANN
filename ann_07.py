# -*- coding: utf-8 -*-
"""ANN_05.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1sM1TD7kDecaWJ8okz_8lZKz7A4VykChB

# Install & Import Libraries
"""

import pandas as pd
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (mean_squared_error, r2_score,
                             mean_absolute_error, explained_variance_score,
                             max_error)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler
plt.rcParams["figure.figsize"] = (12,5)
import warnings
warnings.filterwarnings('ignore')

"""# Load Data"""

# Load and preprocess the dataset
df = pd.read_csv("/content/busan_dataset.csv")
df.columns = df.columns.str.strip()  # Remove spaces from column names
df['Date'] = pd.to_datetime(df['Date'])
df.set_index('Date', inplace=True)

"""# Data Exploration"""

# Display basic information and statistics
print(df.shape, df.info(), df.describe(), df.isna().sum(), sep='\n')

# Feature Engineering
df['hour'] = df.index.hour
df['month'] = df.index.month
required_cols = ['GHI_Average', 'SunZenith_KMU', 'Ambient_Pressure',
                 'Water', 'AOD', 'Uo (atm-cm)', 'CI_Hammer', 'OT', 'hour', 'month']
df = df[required_cols]

df.head()

# Import the required library for color mapping
from itertools import cycle

# Select the last 100 timesteps from the DataFrame
df_last_100 = df.tail(100)

# Create a figure with multiple subplots based on the number of variables
plt.figure(figsize=(15, 20))

# Define a color cycle from the 'tab10' colormap to assign different colors to each variable
color_cycle = cycle(plt.cm.tab10.colors)

# Loop through each column and create a line plot with a unique color
for i, column in enumerate(df_last_100.columns, 1):
    plt.subplot(len(df_last_100.columns), 1, i)  # Create a subplot for each variable
    plt.plot(df_last_100.index, df_last_100[column], label=column, color=next(color_cycle))  # Use different colors
    plt.title(f'Line Graph for {column} - Last 100 Data Points')
    plt.xlabel('Date')
    plt.ylabel(column)
    plt.legend(loc="upper right")

# Adjust layout to prevent overlap
plt.tight_layout()

# Display the plot
plt.show()

# Correlation Matrix
correlation_matrix = df.corr()
plt.figure(figsize=(12, 8))
sns.heatmap(correlation_matrix, annot=True, cmap='seismic', linewidths=0.75, fmt=".2f")
plt.title('Correlation Matrix of Input Variables')
plt.show()

"""# Data Preprocessing"""

# Split the dataset
train_ratio, test_ratio, validation_ratio = 0.7, 0.15, 0.15
train_size = int(len(df) * train_ratio)
test_size = int(len(df) * test_ratio)
train, test, validation = df.iloc[:train_size], df.iloc[train_size:train_size + test_size], df.iloc[train_size + test_size:]

# Input Scaling
cols = ['SunZenith_KMU', 'Ambient_Pressure', 'Water', 'AOD',
        'OT', 'Uo (atm-cm)', 'CI_Hammer', 'hour', 'month']

scaler = RobustScaler()
train[cols] = scaler.fit_transform(train[cols])
test[cols] = scaler.transform(test[cols])

# Scaling GHI
GHI_scaler = RobustScaler()
GHI_scaler.fit(train[['GHI_Average']])
train['GHI_Average'] = GHI_scaler.transform(train[['GHI_Average']])
test['GHI_Average'] = GHI_scaler.transform(test[['GHI_Average']])

print(f'Train size: {len(train)}, Test size: {len(test)}, Validation size: {len(validation)}')

"""# Dataset Building"""

# Dataset Creation Function
def create_dataset(X, y, time_steps=1, horizon=1):
    """Creates dataset for training/testing with a specified horizon."""
    Xs, ys = [], []
    for i in range(len(X) - time_steps - horizon + 1):
        Xs.append(X.iloc[i + time_steps - 1].values)  # Previous time step features
        ys.append(y.iloc[i + time_steps + horizon - 1])  # Target variable at the specified horizon
    return np.array(Xs), np.array(ys)

# Set the desired forecasting horizons
horizons = [1, 2, 3]  # 1-hour, 2-hour, and 3-hour ahead

# Create datasets for each horizon
datasets = {}
for h in horizons:
    X_train, y_train = create_dataset(train, train['GHI_Average'], time_steps=1, horizon=h)
    X_test, y_test = create_dataset(test, test['GHI_Average'], time_steps=1, horizon=h)
    datasets[h] = (X_train, y_train, X_test, y_test)

print(f'X_ANN_train shape: {X_ANN_train.shape}, y_ANN_train shape: {y_ANN_train.shape}')

"""# ANN"""

# Model Training, Prediction, and Evaluation for each horizon
results = {}
predictions = {}
for h in horizons:
    X_train, y_train = datasets[h][:2]  # Get the training data for the horizon
    X_test, y_test = datasets[h][2:]  # Get the testing data for the horizon

    # Build and compile the ANN model
    ann_model = tf.keras.Sequential([
        tf.keras.layers.Dense(units=100, activation='relu', input_shape=(X_train.shape[1],)),
        tf.keras.layers.Dropout(rate=0.5),
        tf.keras.layers.Dense(units=1)
    ])

    ann_model.compile(loss='mean_squared_error', optimizer='adam')

    # Train the model
    ann_model.fit(X_train, y_train, epochs=100, batch_size=64, validation_split=0.15, shuffle=False)

    # Predictions
    y_pred = ann_model.predict(X_test)
    y_pred_inv = GHI_scaler.inverse_transform(y_pred.reshape(-1, 1))
    y_test_inv = GHI_scaler.inverse_transform(y_test.reshape(-1, 1))

    # Store predictions for comparison
    predictions[h] = (y_test_inv.flatten(), y_pred_inv.flatten())

    # Evaluation
    def ANN_accuracy_metrics(y_true, y_pred):
        """Calculate and print model performance metrics"""
        metrics = {
            'R^2': r2_score(y_true, y_pred),
            'MAE': mean_absolute_error(y_true, y_pred),
            'MSE': mean_squared_error(y_true, y_pred),
            'RMSE': np.sqrt(mean_squared_error(y_true, y_pred)),
        }
        return metrics

    metrics = ANN_accuracy_metrics(y_test_inv, y_pred_inv)
    results[h] = metrics

# Side-by-Side Comparison Plot
fig, axs = plt.subplots(1, len(horizons), figsize=(18, 6))

# Add a master title for the entire figure
fig.suptitle('ANN GHI Forecasting Comparison', fontsize=17)

for i, h in enumerate(horizons):
    axs[i].plot(predictions[h][0], marker='.', label='True')
    axs[i].plot(predictions[h][1], 'r', label='Predicted')
    axs[i].set_title(f'{h}-Hour Ahead Forecasting')
    axs[i].set_ylabel('GHI')
    axs[i].set_xlabel('Time')
    axs[i].legend()

plt.tight_layout()
plt.show()

# Print the metrics for each horizon
print("\nComparison of Metrics Across Horizons")
for h in horizons:
    print(f"\n{h}-Hour Ahead:")
    for metric, value in results[h].items():
        print(f'{metric}: {value:.4f}')

# Create a list to hold the metrics
metrics_list = []

# Populate the list with results
for h in horizons:
    metrics_list.append({
        'Horizon (Hours)': h,
        'R^2': results[h]['R^2'],
        'MAE': results[h]['MAE'],
        'MSE': results[h]['MSE'],
        'RMSE': results[h]['RMSE']
    })

# Convert the list to a DataFrame
metrics_table = pd.DataFrame(metrics_list)

# Display the metrics table
print("\nComparison of Metrics Across Horizons")
print(metrics_table)

# Extract RMSE values and corresponding horizons
horizons = list(results.keys())
rmse_values = [results[h]['RMSE'] for h in horizons]

# Create a bar graph
plt.figure(figsize=(10, 6))
bars = plt.bar(horizons, rmse_values, color='skyblue')
plt.title('ANN RMSE Comparison Across Forecasting Horizons')
plt.xlabel('Horizon (Hours)')
plt.ylabel('RMSE')
plt.xticks(horizons)  # Ensure all horizons are shown on x-axis
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Add labels on top of the bars
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.4f}',
             ha='center', va='bottom', fontsize=10)

# Show the plot
plt.show()

import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

# Create a figure for the subplots
fig, axs = plt.subplots(1, len(horizons), figsize=(18, 6))

# Add a master title for the entire figure
fig.suptitle('ANN Regression Plot', fontsize=17)

# Function to plot linear regression on a given axis
def plot_linear_regression(ax, y_true, y_pred, title, r2_value):
    model = LinearRegression()
    model.fit(y_true.reshape(-1, 1), y_pred)  # Fit model

    # Create points for the regression line
    x_line = np.linspace(y_true.min(), y_true.max(), 100).reshape(-1, 1)
    y_line = model.predict(x_line)

    ax.scatter(y_true, y_pred, label='Predictions', alpha=0.5)
    ax.plot(x_line, y_line, color='red', linewidth=2, label='Regression Line')
    ax.set_xlabel('Actual GHI Value')
    ax.set_ylabel('Predicted GHI Value')
    ax.set_title(title)
    ax.set_xlim([y_true.min(), y_true.max()])
    ax.set_ylim([y_pred.min(), y_pred.max()])
    ax.axline((0, 0), slope=1, color='grey', linestyle='--')  # Diagonal line for reference
    ax.text(0.9, 0.1, f'R² = {r2_value:.4f}', transform=ax.transAxes, ha='right', va='bottom')
    ax.legend()
    ax.grid()

# Plotting linear regression for each horizon in subplots
for i, h in enumerate(horizons):
    y_true = predictions[h][0]  # Actual GHI values
    y_pred = predictions[h][1]   # Predicted GHI values
    r2_value = results[h]['R^2'] # R² value

    title = f'Linear Regression for {h}-Hour Ahead Forecasting'
    plot_linear_regression(axs[i], y_true, y_pred, title, r2_value)

# Adjust layout
plt.tight_layout()
plt.show()

import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

# Function to plot linear regression
def plot_linear_regression(y_true, y_pred, title, r2_value):
    model = LinearRegression()
    model.fit(y_true.reshape(-1, 1), y_pred)  # Fit model

    # Create points for the regression line
    x_line = np.linspace(y_true.min(), y_true.max(), 100).reshape(-1, 1)
    y_line = model.predict(x_line)

    plt.figure(figsize=(8, 6))
    plt.scatter(y_true, y_pred, label='Predictions', alpha=0.5)
    plt.plot(x_line, y_line, color='red', linewidth=2, label='Regression Line')
    plt.xlabel('Actual GHI Value')
    plt.ylabel('Predicted GHI Value')
    plt.title(title)
    plt.xlim([y_true.min(), y_true.max()])
    plt.ylim([y_pred.min(), y_pred.max()])
    plt.axline((0, 0), slope=1, color='grey', linestyle='--')  # Diagonal line for reference
    plt.text(0.1, 0.9, f'R² = {r2_value:.4f}', transform=plt.gca().transAxes)
    plt.legend()
    plt.grid()
    plt.show()

# Plotting linear regression for each horizon
for h in horizons:
    y_true = predictions[h][0]  # Actual GHI values
    y_pred = predictions[h][1]   # Predicted GHI values
    r2_value = results[h]['R^2'] # R^2 value

    title = f'Linear Regression for {h}-Hour Ahead Forecasting'
    plot_linear_regression(y_true, y_pred, title, r2_value)

"""------"""

# Create a DataFrame to store the results
results_df = pd.DataFrame()

# Add the Date column
results_df['Date'] = test.index[:len(predictions[1][0])]

# Add actual GHI values (ensure length matches)
actual_ghi_values = GHI_scaler.inverse_transform(test['GHI_Average'].values.reshape(-1, 1)).flatten()
results_df['Actual GHI'] = actual_ghi_values[:len(predictions[1][0])]

# Add predictions for each horizon
for h in horizons:
    pred_col_name = f'Predicted GHI ({h}-Hour Ahead)'
    pred_values = predictions[h][1]  # Get prediction values

    # Align lengths by truncating or filling with NaN
    if len(pred_values) > len(results_df):
        pred_values = pred_values[:len(results_df)]
    else:
        pred_values = np.concatenate((pred_values, [np.nan] * (len(results_df) - len(pred_values))))

    results_df[pred_col_name] = pred_values

# Save to CSV
results_df.to_csv('ANN_ghi_predictions.csv', index=False)

print("CSV file 'ANN_ghi_predictions.csv' has been created successfully.")

# Save to Excel
results_df.to_excel('ANN_ghi_predictions.xlsx', index=False)
print("Excel file 'ANN_ghi_predictions.xlsx' has been created successfully.")

results_df.head()