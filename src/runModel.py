import pandas as pd
import numpy as np
import os
from datetime import datetime
from model import weatherDemandForecast
import math

#changing directory
os.chdir(f'{os.getcwd()}/src')

dataSeason = "fall"
splitData = True

#first reading in data starting with demand and converting Hour Ending to datetime
demandData = pd.read_excel("../data/Native_Load_2021.xlsx",usecols=["UpdatedDate","ERCOT"])
demandData["UpdatedDate"] = pd.to_datetime(demandData["UpdatedDate"], format='%m/%d/%Y %H:%M', infer_datetime_format=True)


#reading in weather data and converting datetime to datetime format
weatherData = pd.read_csv(f"../data/{dataSeason}Data.csv",usecols=["datetime","temp"])
weatherData["datetime"] = pd.to_datetime(weatherData["datetime"],format='%m/%d/%Y %H:%M',infer_datetime_format=True)

#if split data is true we split one half for training model and other half for testing
if(splitData):
    splitIndex = math.ceil(round(len(weatherData["datetime"])/24.0)/2)*24
    trainingData = weatherData.iloc[0:splitIndex]
    testingData =  weatherData.iloc[splitIndex:int(len(weatherData["datetime"]))]     
else:
    trainingData = weatherData


#merging the two data on weather data side
mergedData = trainingData.merge(demandData,left_on="datetime",right_on="UpdatedDate",how="left")[["datetime","temp","ERCOT"]]
mergedData = mergedData.rename(columns = {"ERCOT":"energyDemand","temp":"histWeather"})


maxWeather = np.max(mergedData["histWeather"])
minWeather = np.min(mergedData["histWeather"])

weatherBinStep = 5
masterDataset = {"Datasets":[],"WeatherBins":np.arange(minWeather,maxWeather,weatherBinStep),"weatherBinIndicator":np.zeros((int((len(mergedData["datetime"])/24)),24,int(len(np.arange(minWeather,maxWeather,weatherBinStep)))))}



for day in np.arange(len(mergedData["datetime"])/24):
    #going through each day and splitting data into 24 hour datasets
    masterDataset["Datasets"].append(mergedData[int(day*24):int(((day+1)*24))])
    masterDataset["Datasets"][int(day)] = masterDataset["Datasets"][int(day)].reset_index()

#now going through and creating weather bin dataset
for day in np.arange(len(masterDataset["Datasets"])):
    for hour in  np.arange(len(masterDataset["Datasets"][0])):
        
        #go through weather bins and find closest
        closestWeatherBinIndex = np.abs(masterDataset["WeatherBins"] - masterDataset["Datasets"][day]["histWeather"][hour]).argmin()

        #assign the closet weather bin value as true (1) while leaving others as false
        masterDataset["weatherBinIndicator"][day][hour][closestWeatherBinIndex] = 1


#getting start time
startRun = datetime.now()
start_time = startRun.strftime("%H:%M:%S")
print("Start time:", start_time)


#run model
weatherDemandForecast.main(f"{dataSeason}Run",masterDataset)


#getting end time
endRun = datetime.now()
end_time = endRun.strftime("%H:%M:%S")
print("Run over:", end_time)

#printing total model runtime
print("Total model time took: ",str(endRun-startRun))




#now comparing testing data
weatherModelParameters = pd.read_excel(f"../modelOutputs/{dataSeason}Run.xlsx",sheet_name="weatherScalingDv")
timeModelParameters = pd.read_excel(f"../modelOutputs/{dataSeason}Run.xlsx",sheet_name="timeScalingDv")



#now creating testingOutputDataFile
#merging the two data on weather data side for testing
mergedTestingData = testingData.merge(demandData,left_on="datetime",right_on="UpdatedDate",how="left")[["datetime","temp","ERCOT"]]
mergedTestingData = mergedTestingData.rename(columns = {"ERCOT":"energyDemand","temp":"histWeather"})

testingOutputDataset = pd.DataFrame(np.zeros((len(mergedTestingData["datetime"]),5)),columns=["temperature","prediction","actual","raw difference", "percent error"])

#first creating weather bin indicator for testing dataset
weatherBinIndicator = np.zeros((len(masterDataset["WeatherBins"]),len(mergedTestingData["datetime"])))
for hour in np.arange(len(mergedTestingData["datetime"])):
    
    #go through weather bins and find closest
    closestWeatherBinIndex = np.abs(masterDataset["WeatherBins"] - mergedTestingData["histWeather"][hour]).argmin()

    #assign the closet weather bin value as true (1) while leaving others as false
    weatherBinIndicator[int(closestWeatherBinIndex)][int(hour)] = 1



#generating output
for hour in np.arange(len(mergedTestingData["datetime"])):
    hour24Index = int(hour%24)
    testingOutputDataset["temperature"][hour] = mergedTestingData["histWeather"][hour]
    testingOutputDataset["prediction"][hour] = sum((weatherBinIndicator[b][hour]*weatherModelParameters["weatherScaling"][b]*mergedTestingData["histWeather"][hour]) 
                                            for b in np.arange(len(masterDataset["WeatherBins"]))) + timeModelParameters["timeScaling"][int(hour%24)]*hour24Index
    testingOutputDataset["actual"][hour] = mergedTestingData["energyDemand"][hour]
    testingOutputDataset["raw difference"][hour] = testingOutputDataset["prediction"][hour] - testingOutputDataset["actual"][hour]
    testingOutputDataset["percent error"][hour] = np.abs(testingOutputDataset["raw difference"][hour]/testingOutputDataset["actual"][hour])*100
        
        
        
#now saving testing output to excel file
excelOutputFileName = f"../modelOutputs/{dataSeason}Testing.xlsx"
with pd.ExcelWriter(excelOutputFileName) as writer:  
    testingOutputDataset.to_excel(writer,sheet_name='testingModel')

avgPercentError = np.sum(testingOutputDataset["percent error"])/len(testingOutputDataset["percent error"])
print(f"Average percent error in testing: {avgPercentError}")
print(f"Model output results saved to {excelOutputFileName}")
        