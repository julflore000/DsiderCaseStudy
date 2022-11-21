import sys
import urllib.request
import csv
import codecs
import pandas as pd
import os

class weatherDataCollection:
    
    def main(dataInputs):
        """calls visual crossing weather API and returns the next 15 days of hourly temperature forecast in csv format

        Args:
            dataInputs (dict): dict containing required user inputs for obtaining data (see keys below)
                "lat": latitude of location
                "long": longitude of location
                "userKey": unique visual crossing user API key
        """
        trainingRequestUrl = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{}%2C{}/{}/{}?unitGroup=us&elements=datetime%2Ctemp&include=hours&key={}&contentType=csv".format(dataInputs["lat"],dataInputs["long"],dataInputs["TrainingDateRange"][0],dataInputs["TrainingDateRange"][1],dataInputs["userKey"])
        forecastRequestUrl = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{}%2C{}/{}/{}?unitGroup=us&elements=datetime%2Ctemp&include=hours&key={}&contentType=csv".format(dataInputs["lat"],dataInputs["long"],dataInputs["ForecastDateRange"][0],dataInputs["ForecastDateRange"][1],dataInputs["userKey"])

        try: 
            #read directly in from csv format of the data url-if verification is needed, the process will fail
            trainingWeatherDf = pd.read_csv(trainingRequestUrl)
            forecastRequestDf = pd.read_csv(forecastRequestUrl)
        except Exception as e:
            print("Error in request of weather data")
            print(e)
            sys.exit()

        #saving two files to energyDemand folder
        trainingWeatherDf.to_csv("../energyDemandData/trainingData.csv")
        forecastRequestDf.to_csv("../energyDemandData/forecastData.csv")
        
'''       
os.chdir(f'{os.getcwd()}/src') 
#userKey switch
#userKey = "USFUDWAANQJAA7SLT6MG4JXMT"
#userKey = "64MQ5Q5XXU3WA4EKL26EMEDKK"
       
weatherDataInput = {"lat":31.026018,
            "long":-96.485245,
            "userKey":userKey,
            "TrainingDateRange": ["2022-11-05","2022-11-18"],
            "ForecastDateRange": ["2022-11-19","2022-12-03"]
            }

#running test of weather API data call


#weatherDataCollection.main(weatherDataInput)
'''
