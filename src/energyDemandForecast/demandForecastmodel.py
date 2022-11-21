from fileinput import filename
from pyomo.environ import *
from pyomo.opt import SolverFactory
import pyomo as pyo
from pytest import param
import pandas as pd
import numpy as np
import os.path
import math



#model 1 looks at each individual datapoint
#input weather list
#Match up weather data with closest weather values
#select closest weather for at least 2 data points (if other values are close include them)


#give range of prior values



class weatherDemandForecast:          
        
    def writeDataFile(dataFileName,inputDataset):
        with open('../modelInputs/'+str(dataFileName)+'.dat', 'w') as f:
            
            
            #horizon (time) set-if hourly will be 0-23
            f.write('set horizon := ')
            for i in range(len(inputDataset["Datasets"][0])):
                f.write('%d ' % i)
            f.write(';\n\n')

            #amount of datasets which we are training the model on
            f.write('set datasets := ')
            for i in range(len(inputDataset["Datasets"])):
                f.write('%d ' % i)
            f.write(';\n\n')
            
            #amount of weather bins to create
            f.write('set weatherBins := ')
            for i in range(len(inputDataset["WeatherBins"])):
                f.write('%d ' % i)
            f.write(';\n\n')
            
            #now writing up param data for double index params
            paramNames = ["energyDemand","histWeather"]
            
            #looping through each param
            for paramName in paramNames:
                f.write('param %s := \n' % (paramName))
                for i in range(len(inputDataset["Datasets"])):
                    for j in range(len(inputDataset["Datasets"][0])):
                        if((i == len(inputDataset["Datasets"])-1) and (j == len(inputDataset["Datasets"][0])-1)):
                            f.write('%d %d %f' % (i,j,inputDataset["Datasets"][i][paramName][j]))     
                        else:
                            f.write('%d %d %f \n' % (i,j,inputDataset["Datasets"][i][paramName][j]))
                f.write(';\n\n')

            #then writing up structure for weather bin indicator-different from above two params
            paramName = "weatherBinIndicator"
            f.write('param %s := \n' % (paramName))
            for i in range(len(inputDataset["Datasets"])):
                for j in range(len(inputDataset["Datasets"][0])):
                    for bin in range(len(inputDataset["WeatherBins"])):
                        if((i == len(inputDataset["Datasets"])-1) and (j == len(inputDataset["Datasets"][0])-1) and (bin == len(inputDataset["WeatherBins"])-1)):
                            f.write('%d %d %d %f' % (i,j,bin,inputDataset[paramName][i][j][bin]))                    
                        else:
                            f.write('%d %d %d %f \n' % (i,j,bin,inputDataset[paramName][i][j][bin]))
            f.write(';\n\n')
                            
            print("Completed data file")
            

    def main(dataFileName,inputDataset,testMode=False):
        """Hourly forecast of demand data from weather and time of day

        Args:
            dataFileName (str): .dat file name which will read in/be created data for model run
            inputDataset (dict): see README for further clarification on what parameters are expected to be inputted into spreadsheet
            testMode (bool): automatically set to false, if true-will delete the .dat input file and output file associated with the dataFileName
        """ 
        #deleting files if test mode is activated
        if(testMode):
            try:
                os.remove(f"../modelInputs/{dataFileName}.dat")
                os.remove(f"../modelOutputs/{dataFileName}.xlsx")
            except:
                print("Test mode activated but one of files already deleted")
        
            
        
        # creating optimization model with pyomo abstract representation
        model = AbstractModel()

        ################### START SETS  ###################
        #timesteps in simulation
        model.horizon = RangeSet(0,len(inputDataset["Datasets"][0])-1)
        
        #number of unique datasets (days) which we are training the model on
        model.datasets = RangeSet(0,len(inputDataset["Datasets"])-1)
        
        #number of different weather bins to create unique scaling parameters for
        model.weatherBins = RangeSet(0,len(inputDataset["WeatherBins"])-1)
        ################### END SETS  ###################


        
        ################### START PARAMETERS  ###################
        #energy demand for each dataset for each hour
        model.energyDemand = Param(model.datasets,model.horizon)

        #historical weather for each dataset on hourly basis
        model.histWeather = Param(model.datasets,model.horizon)

        #weather bin structure (i.e. indicator variable on what weather bin the histWeather is in)
        model.weatherBinIndicator = Param(model.datasets,model.horizon,model.weatherBins)    
        ################### END PARAMETERS  ###################
        
        
        
        
        ################### START DECISION VARIABLES  ###################
        #hourly weather scaling parameter
        model.weatherScaling= Var(model.weatherBins,domain=Reals)

        #hourly time scaling parameter
        model.timeScaling = Var(model.horizon,domain=Reals,initialize=0)
        
        #hourlyDeviation from training data broken down by dataset
        model.hourlyDeviation = Var(model.datasets,model.horizon,domain=Reals)
        
        #positive and negative deviation defintions
        model.deviationPositive = Var(domain=NonNegativeReals)
        model.deviationNegative = Var(domain=NegativeReals)
        ################### END DECISION VARIABLES    ###################
        
        
        
###################     START OBJECTIVE     ###################


        def minDeviation_rule(model):
            return(sum(sum(model.hourlyDeviation[d,t] for t in model.horizon) for d in model.datasets))
            #return (model.deviationPositive - model.deviationNegative)
        
        model.trainingDeviation = Objective(rule = minDeviation_rule, sense = minimize)
        
        ###################       END OBJECTIVE     ###################
    
        ###################       START CONSTRAINTS     ###################
        #deviation definition for a specific model
        def positiveDeviationConstraint(model,d,t):
            return(model.hourlyDeviation[d,t] >= (sum((model.weatherBinIndicator[d,t,b]*model.weatherScaling[b]*model.histWeather[d,t]) 
                                                    for b in model.weatherBins) +
                                                model.timeScaling[t]*t - model.energyDemand[d,t]))
        model.positiveDeviationConstraint = Constraint(model.datasets,model.horizon,rule=positiveDeviationConstraint)


        #deviation definition for a specific model
        def negativeDeviationConstraint(model,d,t):
            return(model.hourlyDeviation[d,t] >= (sum((-1*model.weatherBinIndicator[d,t,b]*model.weatherScaling[b]*model.histWeather[d,t]) 
                                                    for b in model.weatherBins) -
                                                model.timeScaling[t]*t + model.energyDemand[d,t]))
        model.negativeDeviationConstraint = Constraint(model.datasets,model.horizon,rule=negativeDeviationConstraint)

        #keep deviation small
        '''        def keepTopDeviationSmallConstraint(model,d,t):
            return(7000 >= (sum( (model.weatherBinIndicator[d,t,b]*model.weatherScaling[b]*model.histWeather[d,t]) 
                                                    for b in model.weatherBins) +
                                                model.timeScaling[t]*t) - model.energyDemand[d,t])
        model.keepTopDeviationSmallConstraint = Constraint(model.datasets,model.horizon,rule=keepTopDeviationSmallConstraint)
        
        def keepBottomDeviationSmallConstraint(model,d,t):
            return(-7000 <= (sum( (model.weatherBinIndicator[d,t,b]*model.weatherScaling[b]*model.histWeather[d,t]) 
                                                    for b in model.weatherBins) +
                                                model.timeScaling[t]*t) - model.energyDemand[d,t])
        model.keepBottomDeviationSmallConstraint = Constraint(model.datasets,model.horizon,rule=keepBottomDeviationSmallConstraint)
        '''   
        ###################       END   CONSTRAINTS     ###################
    


        ###################          WRITING DATA       ###################
        if(os.path.isfile(f"../dataInputs/{dataFileName}.dat")):
            print(f"Data file {dataFileName} already exists!\nSkipping creating .dat file")
        else:
            #print(f"Data file {dataFileName} does not exist.\nCreating .dat file")
            weatherDemandForecast.writeDataFile(dataFileName,inputDataset)
        
        # load in data for the system
        data = DataPortal()
        data.load(filename=f"../modelInputs/{dataFileName}.dat", model=model)
        instance = model.create_instance(data)
                
        
        
        solver = SolverFactory('glpk')
        result = solver.solve(instance)
        #instance.display()
        
        #setting up structure in order to get out decision variables (and objective) and save in correct excel format

        weatherScalingDataset = pd.DataFrame(np.zeros(len(inputDataset["WeatherBins"])), columns=["weatherScaling"])

        timeScalingDataset = pd.DataFrame(np.zeros(24),columns=["timeScaling"])


        predictionDataset = pd.DataFrame(np.zeros((24*len(inputDataset["Datasets"]),5)),columns=["temperature","prediction","actual","raw difference", "percent error"])

        #assigning dvs based on weather bins
        for bin in np.arange(len(inputDataset["WeatherBins"])):
            weatherScalingDataset["weatherScaling"][bin] = instance.weatherScaling[bin].value       


        #assigning hourly dvs for time scaling
        for hour in np.arange(24):
            #print(instance.timeScaling[hour].value)
            timeScalingDataset["timeScaling"][hour] = instance.timeScaling[hour].value          
        
        #assigning predication data and real data
        hour = 0
        for dataset in instance.datasets:
            for t in instance.horizon:
                predictionDataset["temperature"][hour] = instance.histWeather[dataset,t]
                predictionDataset["prediction"][hour] = sum((instance.weatherBinIndicator[dataset,t,b]*instance.weatherScaling[b].value*instance.histWeather[dataset,t]) 
                                                        for b in instance.weatherBins) + instance.timeScaling[t].value*t
                predictionDataset["actual"][hour] = instance.energyDemand[dataset,t]
                predictionDataset["raw difference"][hour] = predictionDataset["prediction"][hour] - predictionDataset["actual"][hour]
                predictionDataset["percent error"][hour] = np.abs(predictionDataset["raw difference"][hour]/predictionDataset["actual"][hour])*100
                hour += 1
        
        
        
        
        
        #now saving 4 datasets to different sheets in same excel file
        excelOutputFileName = f"../modelOutputs/{dataFileName}.xlsx"
        with pd.ExcelWriter(excelOutputFileName) as writer:  
            weatherScalingDataset.to_excel(writer,sheet_name='weatherScalingDv') 
            
            timeScalingDataset.to_excel(writer,sheet_name='timeScalingDv') 
            
            predictionDataset.to_excel(writer,sheet_name='predicationAnalysis') 
        
        print(f"Model output results saved to {excelOutputFileName}")
        