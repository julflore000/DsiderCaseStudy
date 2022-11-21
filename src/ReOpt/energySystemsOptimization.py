import pandas as pd
import numpy as np
import json
import requests
import copy
import os
import ReOpt.postAndPull

class energySystemsOptimization:
    def main(dataInputs):
        apiKey = dataInputs["apiKey"]
        
        post_1 = {"Scenario": {
                    "include_climate_in_objective": dataInputs["include_climate_in_objective"],
                    "include_health_in_objective": dataInputs["include_health_in_objective"],
                    "Site": {
                        "longitude": dataInputs["long"],
                        "latitude": dataInputs["lat"],
                        #"co2_emissions_reduction_min_pct": .3,
                    "LoadProfile": {
                        "loads_kw": dataInputs["annualLoadProfile"],
                    },
                    "ElectricTariff": {
                        "urdb_label": "5d6588d95457a39b16c68cdd"
                    },
                    "Wind": {
                        "size_class": "commercial",
                        "max_kw": 10000000,
                    }
                }}}
        
        root_url = f"https://developer.nrel.gov/api/reopt/stable"
        resultsFileOutput = "ReOpt/energyOptimizationOutput/results_file.json"
        api_response = ReOpt.postAndPull.get_api_results(post=post_1, 
                                    API_KEY=apiKey, 
                                    api_url=root_url, 
                                    results_file=resultsFileOutput, 
                                    run_id=None)
        
        
        #saving specific tech generation to excel file for geothermal analysis
        