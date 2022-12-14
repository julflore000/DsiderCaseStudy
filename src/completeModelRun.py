import weatherDataCollection.weatherCollection as weatherCollection, energyDemandForecast.runDemandForecast as runDemandForecast,ReOpt.energySystemsOptimization
import os
import pandas as pd
import math
import numpy as np
import json
from datetime import datetime


os.chdir(f'{os.getcwd()}/src')
weatherDataInput = {"lat":31.026018,
            "long":-96.485245,
            "userKey":"",
            "TrainingDateRange": ["2021-11-05","2021-11-18"],
            "ForecastDateRange": ["2021-11-19","2021-12-03"]
            }
#if you get HTTP error 429-youve reached max weather requests

#calling weatherDataRun-not calling right now to avoid hitting request limits
#weatherCollection.weatherDataCollection.main(weatherDataInput)


#then calling energy demand forecast to create demand forecast model on training data
#run model on forecast weather temp data, and save results to excel file
runDemandForecast.energyDemandRun.main()


#then calling final method which call energy systems optimization model (currently ReOpt to optimize energy mix for next two weeks)


#reading in forecast data for optimizing demand profile
forecastData = pd.read_excel("../modelOutputs/forecast.xlsx",usecols=["datetime","energyDemand"])
histEnergyDemand = pd.read_excel("../energyDemandData/Native_Load_2021.xlsx",usecols=["UpdatedDate","ERCOT"])

mergedData = histEnergyDemand.merge(forecastData,left_on="UpdatedDate",right_on="datetime",how="left")

completeLoadProfile = []

for rowIndex in mergedData.index:
    if(math.isnan(mergedData["energyDemand"][rowIndex])):
        completeLoadProfile.append(mergedData["ERCOT"][rowIndex])
    else:
        completeLoadProfile.append(mergedData["energyDemand"][rowIndex])
        
energyOptimizationInputs = {
    "apiKey": "oW0O3wFWAT10rQIklgu9q9tf8AQfZxmCdzhtWkmD",
    "lat":31.026018,
    "long":-96.485245,
    "annualLoadProfile": completeLoadProfile,
    "include_climate_in_objective": True,
    "include_health_in_objective": True,
}

#runs energy optimization model and saves into a results_file
ReOpt.energySystemsOptimization.energySystemsOptimization.main(energyOptimizationInputs)






###GEOTHERMAL ANALYSIS
#now getting data and saving hourly generation by each technology to excel format
f = open('ReOpt/energyOptimizationOutput/results_file.json')
  
# returns JSON object as 
# a dictionary
data = json.load(f)
  
  
#creating pandas array with columns of interest
finalEnergyOutput = {}


#putting in info to final data output
finalEnergyOutput["totalLoad"] = completeLoadProfile

finalEnergyOutput["storageDischarge"] = data["outputs"]["Scenario"]["Site"]["Storage"]["year_one_to_load_series_kw"]
finalEnergyOutput["pvGen"] = data["outputs"]["Scenario"]["Site"]["PV"]["year_one_to_load_series_kw"]
finalEnergyOutput["windGen"] = data["outputs"]["Scenario"]["Site"]["Wind"]["year_one_to_load_series_kw"]
finalEnergyOutput["gridSupply"] = np.array(completeLoadProfile) - (np.array(finalEnergyOutput["storageDischarge"]) + np.array(finalEnergyOutput["pvGen"]) + np.array(finalEnergyOutput["windGen"]))

#converting dict to pandas dataframe and then saving to excel
pdEnergyDf = pd.DataFrame.from_dict(finalEnergyOutput)

#selecting out the hours we are only interested in
janFirst = "2021-01-01T00:00:00"
firstForecastDate = forecastData["datetime"][0] 
secondForecastDate = forecastData["datetime"][len(forecastData["datetime"])-1] 

date_format_str = '%Y-%m-%dT%H:%M:%S'

startIndex = (datetime.strptime(firstForecastDate, date_format_str) - datetime.strptime(janFirst, date_format_str)).total_seconds()/3600
endIndex = (datetime.strptime(secondForecastDate, date_format_str) - datetime.strptime(janFirst, date_format_str)).total_seconds()/3600

#indexing out data
forecastDf = pdEnergyDf.iloc[int(startIndex):(int(endIndex)+1)]

forecastDf["datetime"] = forecastData["datetime"].to_numpy()

#geothermalDemand array for when we want electricity
geothermalDemand = []

for row in forecastDf.index:
    if(forecastDf["gridSupply"][row] <= 1):
        geothermalDemand.append(1)
    else:
        geothermalDemand.append(0)        

#putting into df
forecastDf["geothermalElecNeed"] = geothermalDemand

#reordering df
forecastDf = forecastDf[['datetime', 'pvGen', 'windGen', 'storageDischarge', 'gridSupply','geothermalElecNeed']]

#writing final output to simulationOutput folder
forecastDf.to_excel("../simulationOutput/energyAnalysis.xlsx",index=False)
