# -*- coding: utf-8 -*-
"""
Created on Wed May 13 13:17:31 2020

@author: danie
"""
# # Below Code is to conduct a pre-optimization analysis of the impact of design, operational and resilience models
# with the design of battery, rotors (inceasing complexity) and operable heights at each of the resilience policy.
# This will help to observe the trends of the model functions with the design variables and to see the overall
# feasible design space. I (Arpan) will document it in Jupyter note after the analysis.

# # The arguments of the Operational model changes for the sake of the analysis, thus I have kept the models,
# rather than importing from the original file. The models in the original files will be used in optimization framework
# It is better to separate this file (model analysis) with the original model and optimization file, since
# this file is for analysis purpose only and is subject to frequent changes in model arguments.

# # The file currently takes about 25-30 mins to run. The whole analysis will be saved in "Cost_eval.csv".
# To save time on running the file again, you can look into the already saved .csv file instead
import sys

sys.path.append('../')

import fmdtools.faultsim.propagate as propagate
import fmdtools.resultdisp as rd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from drone_mdl import *
import time
import pandas as pd
import numpy as np

# Design Model
def x_to_dcost(xdes):
    bats = ['monolithic', 'series-split', 'parallel-split', 'split-both']
    linarchs = ['quad', 'hex', 'oct']
    batcostdict = {'monolithic': 0, 'series-split': 50000, 'parallel-split': 50000, 'split-both': 100000}
    linecostdict = {'quad': 0, 'hex': 100000, 'oct': 200000}
    # print(xdes[0])
    descost = batcostdict[bats[xdes[0]]] + linecostdict[linarchs[xdes[1]]]
    return descost


# Operation Model
# Constraints   - batteries stay above 20% (to avoid damage) #postitive means violation
#               - no faults at end of simulation # True means faults exists (violation)
#               - cannot fly above 122 m (400 ft) #Positive means violation ??
def calc_oper(mdl):
    endresults_nom, resgraph, mdlhist = propagate.nominal(mdl)
    opercost = endresults_nom['classification']['expected cost']
    g_soc = 20 - mdlhist['functions']['StoreEE']['soc'][-1]
    g_faults = any(endresults_nom['faults'])
    g_max_height = sum([i for i in mdlhist['flows']['DOFs']['elev'] - 122 if i > 0])
    return opercost, g_soc, g_faults, g_max_height


def x_to_ocost(xdes, xoper, xres):
    bats = ['monolithic', 'series-split', 'parallel-split', 'split-both']
    linarchs = ['quad', 'hex', 'oct']
    respols = ['continue', 'to_home', 'to_nearest', 'emland']
    # start locs
    target = [0, 150, 160, 160]
    safe = [0, 50, 10, 10]
    start = [0.0, 0.0, 10, 10]

    sq = square(target[0:2], target[2], target[3])
    fp = plan_flight(xoper[0], sq, start[0:2] + [0])
    params = {'bat': bats[xdes[0]], 'linearch': linarchs[xdes[1]], 'flightplan': fp,
              'respolicy': {'bat': respols[xres[0]], 'line': respols[xres[1]]}, 'target': target, 'safe': safe,
              'start': start, 'loc': 'rural'}
    # params = {'bat': bats[xdes[0]], 'linearch': linarchs[xdes[1]], 'flightplan': fp,
    #           'target': target, 'safe': safe, 'start': start}
    mdl = Drone(params=params)
    return calc_oper(mdl)


# Resilience Model
def calc_res(mdl):
    app = SampleApproach(mdl, faults='single-component', phases={'forward'})
    endclasses, mdlhists = propagate.approach(mdl, app, staged=True)
    rescost = rd.process.totalcost(endclasses)
    return rescost


def x_to_rcost(xdes, xoper, xres):
    bats = ['monolithic', 'series-split', 'parallel-split', 'split-both']
    linarchs = ['quad', 'hex', 'oct']
    respols = ['continue', 'to_home', 'to_nearest', 'emland']
    # start locs
    target = [0, 150, 160, 160]
    safe = [0, 50, 10, 10]
    start = [0.0, 0.0, 10, 10]

    sq = square(target[0:2], target[2], target[3])
    fp = plan_flight(xoper[0], sq, start[0:2] + [0])

    params = {'bat': bats[xdes[0]], 'linearch': linarchs[xdes[1]], 'flightplan': fp,
              'respolicy': {'bat': respols[xres[0]], 'line': respols[xres[1]]}, 'target': target, 'safe': safe,
              'start': start, 'loc': 'rural'}
    mdl = Drone(params=params)
    return calc_res(mdl)



#################################################################################################
## Creating test design grid matrix
xbat = pd.Series([0, 1, 2, 3])  # 4 choices
xrot = pd.Series([0, 1, 2])  # 3 choices
xh = pd.Series(np.arange(10, 122, 10))  # Discritized into 12 different heights for computational efficiency
xrespolbat = pd.Series([0, 1, 2, 3])
xrespolrot = xrespolbat

# Generating grid matrix with each combination of design variables (bat, rotor and height) at any fixed level of resilience policy
xbat_grid = pd.concat([pd.concat([xbat.repeat(xrot.size * xh.size)] * 1, ignore_index=True)] * xrespolbat.size,
                      ignore_index=True)
xrot_grid = pd.concat([pd.concat([xrot.repeat(xh.size)] * xbat.size, ignore_index=True)] * xrespolbat.size,
                      ignore_index=True)
xh_grid = pd.concat([pd.concat([xh] * (xbat.size * xrot.size), ignore_index=True)] * xrespolbat.size, ignore_index=True)
xrespolbat_grid = pd.concat([xrespolbat.repeat(xbat.size * xrot.size * xh.size)] * 1, ignore_index=True)
xrespolrot_grid = xrespolbat_grid
col_names = ["Bat", "Rotor", "Height", "ResPolBat", "ResPolRot"]
x_mat = pd.concat([xbat_grid, xrot_grid, xh_grid, xrespolbat_grid, xrespolrot_grid], axis=1, ignore_index=True)
x_mat = pd.DataFrame(x_mat.values, columns=col_names)
# pd.set_option("display.max_rows", None, "display.max_columns", None)
# print(x_mat)
## Initializing dataframe for storing respective cost values and constraint validation for each row of x_mat (design choices)
Cost_eval = pd.DataFrame(columns=['desC', 'operC', 'resC', 'c1', 'c2', 'c3', 'c_cum'])
# Evaluating design, operational and resilience models at the design grid points
for ix in range(len(x_mat)):
    xdes = [x_mat.iloc[ix, 0], x_mat.iloc[ix, 1]]
    xoper = [x_mat.iloc[ix, 2]]
    xres = [x_mat.iloc[ix, 3], x_mat.iloc[ix, 4]]
    desC = x_to_dcost(xdes)  # Calling design model
    operC = x_to_ocost(xdes, xoper, xres)  # Calling operational model
    resC = x_to_rcost(xdes, xoper, xres)  # Calling failure model
    Cost_eval.loc[ix, ['desC']] = desC
    Cost_eval.loc[ix, ['operC']] = operC[0]
    Cost_eval.loc[ix, ['resC']] = resC
    # Constraints validation at each design grid points: 1=violation, 0=no violation
    if operC[1] > 0:  # Violation: batteries below 20% (to avoid damage)
        Cost_eval.loc[ix, ['c1']] = 1
    else:
        Cost_eval.loc[ix, ['c1']] = 0

    if operC[2] == True:  # Violation: faults at end of simulation
        Cost_eval.loc[ix, ['c2']] = 1
    else:
        Cost_eval.loc[ix, ['c2']] = 0

    if operC[3] > 0:  # Violation: fly above 122 m
        Cost_eval.loc[ix, ['c3']] = 1
    else:
        Cost_eval.loc[ix, ['c3']] = 0

    if ((operC[1] > 0 or operC[2] == True) or (operC[3] > 0)):  # Infeasible design if any above constraints violated
        Cost_eval.loc[ix, ['c_cum']] = 1
    else:
        Cost_eval.loc[ix, ['c_cum']] = 0

pd.set_option("display.max_rows", None, "display.max_columns", None)
# print(Cost_eval)
# print(feasible_DS)
# Build a large dataset with the design choice and the respective costs and constraint validation
grid_results = pd.concat([x_mat, Cost_eval], axis=1, ignore_index=True)
grid_results.columns = ['Bat', 'Rotor', 'Height', 'ResPolBat', 'ResPolRot','desC', 'operC', 'resC', 'c1', 'c2', 'c3', 'c_cum']
# Saving the results in .csv file
# We will work on this dataset for plotting (examples provided in the trade-off_Analysis_plot.py)
# No need to rerun the file unless we change the cost models
grid_results.to_csv('grid_results.csv', index=False)
print(grid_results)