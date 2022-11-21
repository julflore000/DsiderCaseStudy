import pandas as pd
import numpy as np
import os
from datetime import datetime
from energyDemandForecast.demandForecastmodel import weatherDemandForecast
import math

class energyDemandRun:

        
    def main():
        #changing directory

        dataSeason = "training"
        splitData = False

        #first reading in data starting with demand and converting Hour Ending to datetime
        demandData = pd.read_excel("../energyDemandData/Native_Load_2021.xlsx",usecols=["UpdatedDate","ERCOT"])
        demandData["UpdatedDate"] = pd.to_datetime(demandData["UpdatedDate"], format='%m/%d/%Y %H:%M', infer_datetime_format=True)


        #reading in weather data and converting datetime to datetime format
        weatherData = pd.read_csv(f"../energyDemandData/{dataSeason}Data.csv",usecols=["datetime","temp"])
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



        for day in np.arange(len(mergedData["datetime"])/24-1):
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


        #now forecasting out model to forecastData
        weatherModelParameters = pd.read_excel(f"../modelOutputs/{dataSeason}Run.xlsx",sheet_name="weatherScalingDv")
        timeModelParameters = pd.read_excel(f"../modelOutputs/{dataSeason}Run.xlsx",sheet_name="timeScalingDv")


        #now creating forecast for two weeks
        #merging the two data on weather data side for forecast
        forecastData = pd.read_csv("../energyDemandData/forecastData.csv",names=["datetime","temp"])
        forecastData =  forecastData.iloc[1: , :]
        forecastData["energyDemand"] = 0.0

        #first creating weather bin indicator for testing dataset
        weatherBinIndicator = np.zeros((len(masterDataset["WeatherBins"]),len(forecastData["datetime"])))
        for hour in np.arange(len(forecastData["datetime"])-1):
            
            #go through weather bins and find closest
            closestWeatherBinIndex = np.abs(masterDataset["WeatherBins"] - float(forecastData["temp"][hour])).argmin()

            #assign the closet weather bin value as true (1) while leaving others as false
            weatherBinIndicator[int(closestWeatherBinIndex)][int(hour)] = 1



        #forecasting the model out to two weeks with input weather data
        for hour in np.arange(len(forecastData["datetime"])-1):
            hour24Index = int(hour%24)
            forecastData["energyDemand"][hour] = sum((weatherBinIndicator[b][hour]*weatherModelParameters["weatherScaling"][b]*float(forecastData["temp"][hour])) 
                                                    for b in np.arange(len(masterDataset["WeatherBins"]))) + timeModelParameters["timeScaling"][int(hour%24)]*hour24Index
    
                
                
        #now saving testing output to excel file
        excelOutputFileName = f"../modelOutputs/forecast.xlsx"
        with pd.ExcelWriter(excelOutputFileName) as writer:  
            forecastData.to_excel(writer,sheet_name='forecastModel')

        print(f"Energy demand forecast saved to {excelOutputFileName}")

                