"""
File: pvSavingSim.py
Author: Jan Philipp Ecker
Date: 2023-08-30

Description: A simple python script that "simulates" the potential savings of a PV system based on data exported from the PVGIS tool:
             https://re.jrc.ec.europa.eu/pvg_tools/en/

"""

# =========================================================
# Module imports
# =========================================================

import json
import csv
import numpy as np
from datetime import datetime
import argparse


# =========================================================
# Arugment parser handling
# =========================================================

parser = argparse.ArgumentParser(prog="pvSavingSim",
                                 description="Simple script to simulate the possibel savings of your PV setup")
parser.add_argument('-i', '--pvgisTimeSeries', metavar='file', action='append', required=True, help='Hourly consumption data exported from PVGIS in json format')
parser.add_argument('-l', '--inverterPowerLimit', metavar='N', type=int, required=True, help='Maximum power of the inverter (in Watt)')
parser.add_argument('-c', '--constantConsumption', metavar='N', type=int, help='The value of the constnat consumption that should be assumed (in Watt)')
args = parser.parse_args()


# =========================================================
# This is my custom handling to estimate the consumption
# based on som real consumption data exported from influxdb
# this part is currently undocumented. If you want to use it
# you have to provide the follwoing array:
# avg_consumption_weekday[day][hour][0]
# with day 0-6, hours 0-23 and 0 storing the consumption
# in W in that hour
# TBD: document / clean this up
# =========================================================
avg_consumption_weekday = {}
for day in range (7):
    avg_consumption_weekday[day] = {}
    for hour in range(24):
        avg_consumption_weekday[day][hour] = {}
        avg_consumption_weekday[day][hour][0] = 0.0
        for phase in range(3):
            avg_consumption_weekday[day][hour][phase+1] = []
            #avg_consumption_weekday[day][hour][phase+1][0] = []
            #avg_consumption_weekday[day][hour][phase+1][1] = 0

with open('data/2023-08-30_17_52_influxdb_data.csv', newline='') as csv_file:
    reader = csv.reader(csv_file, delimiter=',')
    for row in reader:
        # Ignore first lines as it contains comments and column headings
        if(reader.line_num < 5):
            continue;
        
        if(len(row) > 0):
            entry_datetime = datetime.strptime(row[5], '%Y-%m-%dT%H:%M:%SZ')
            entry_value = float(row[6])
            entry_phase = int(row[11][1:])
            entry_dow = int(entry_datetime.strftime("%w"))
            entry_hour = int(entry_datetime.strftime("%H"))

            avg_consumption_weekday[entry_dow][entry_hour][entry_phase].append(entry_value)

for day in range (7):
    for hour in range(24):
        for phase in range(3):
            avg_consumption_weekday[day][hour][0] += np.median(avg_consumption_weekday[day][hour][phase+1])
            #print("consumption", day, hour, avg_consumption_weekday[day][hour][0])


# =========================================================
# Function defintions
# =========================================================

def read_add_production(json_file_name, p_generated):
    with open(json_file_name) as json_file:
        data = json.load(json_file)

        for hourly_data in data['outputs']['hourly']:    
            entry_datetime = datetime.strptime(hourly_data['time'], '%Y%m%d:%H%M')
            entry_value = float(hourly_data['P'])
            entry_doy = int(entry_datetime.strftime("%j"))
            entry_hour = int(entry_datetime.strftime("%H"))

            p_generated[entry_doy][entry_hour] += entry_value

def calculate_and_print_summary(p_generated, p_consumed):
    p_consumed_sum_without_pv = 0.0
    p_consumed_sum_with_pv = 0.0
    p_not_consumed_sum = 0.0
    p_inverter_loss_sum = 0.0

    for day in p_consumed:
        for hour in p_consumed[day]:
            # first cap the generated energy to the limit of the inverter
            if(p_generated[day][hour] > args.inverterPowerLimit):
                p_inverter_loss_sum += p_generated[day][hour]-args.inverterPowerLimit
                p_generated[day][hour] = args.inverterPowerLimit

            p_consumed_sum_without_pv += p_consumed[day][hour]
            p_sum = p_consumed[day][hour]-p_generated[day][hour];
            if(p_sum >= 0):
                p_consumed_sum_with_pv += p_sum
            else:
                p_not_consumed_sum += p_sum*-1
                #print("not consumed", day, hour, p_generated[day][hour], p_consumed[day][hour])

    p_consumed_sum_without_pv = round(p_consumed_sum_without_pv/1000)
    p_consumed_sum_with_pv = round(p_consumed_sum_with_pv/1000)
    p_saved = p_consumed_sum_without_pv-p_consumed_sum_with_pv
    p_not_consumed_sum = round(p_not_consumed_sum/1000)
    p_inverter_loss_sum = round(p_inverter_loss_sum/1000)

    print("")
    print("Yearly power consumption without PV:", p_consumed_sum_without_pv, "kwh")
    print("Yearly power consumption with PV:", p_consumed_sum_with_pv, "kwh")
    print("")
    print("Energy saved: ", p_saved, "kwh")
    print("Estimated savings: ", round(p_saved*0.35, 2), "€")
    print("")
    print("Energy not consumed: ", p_not_consumed_sum, "kwh")
    print("Energy lost by inverter limit: ", p_inverter_loss_sum, "kwh")

def init_dicts(p_generated, p_consumed):
    # create empty dict for the generated energy
    for day in range(366):
        p_generated[day+1] = {}
        for hour in range(24):
            p_generated[day+1][hour] = 0.0

    
    if args.constantConsumption:
        # ==================================
        # Variant 1: Constant consumption 350W
        # ==================================

        # create a simple dict for the consumption for now
        for day in range(366):
            p_consumed[day+1] = {}
            for hour in range(24):
                p_consumed[day+1][hour] = args.constantConsumption
    else:
        # ==================================
        # Variant 2: Median consumption from actual data
        # TBD: Currently the year starts with weekday 0, we don't care about matching the correct day
        #      I assume it should not have any impact as it should average out over the year
        # ==================================
        weekday = 0
        for day in range(366):
            p_consumed[day+1] = {}
            for hour in range(24):
                p_consumed[day+1][hour] = avg_consumption_weekday[weekday][hour][0]

            weekday = weekday +1 if weekday < 6 else 0


p_generated = {}
p_consumed = {}


# =========================================================
# Run the "simulation" and print the output
# =========================================================

init_dicts(p_generated, p_consumed)

for time_series in args.pvgisTimeSeries:
    read_add_production(time_series, p_generated)

calculate_and_print_summary(p_generated, p_consumed)