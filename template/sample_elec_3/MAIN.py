import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib
from datetime import datetime

from platypus import Problem, Integer, nondominated
from platypus import NSGAII, NSGAIII
from platypus import ProcessPoolEvaluator

from simulation import Simulation
from evaluation.economics import Economics
from evaluation.performance import Performance

'''
Optimization approach:
    1. Define optimization problem inside optimization class
    2. Initialize optimization problem and apply optimization method to it
    3. Evaluate optimization results and eventually neglect dominated results
    
Different optimization methods can be loaded, according to Platypus:
    NSGAII,
    (NSGAIII, {"divisions_outer":12}),
    (CMAES, {"epsilons":[0.05]}),
    GDE3,
    IBEA,
    (MOEAD, {"weight_generator":normal_boundary_weights, "divisions_outer":12}),
    (OMOPSO, {"epsilons":[0.05]}),
    SMPSO,
    SPEA2,
    (EpsMOEA, {"epsilons":[0.05]})
'''

#%% Problem definition inside optimization class

class system_optimisation(Problem):
    '''
    This is central optimization class based on the evolutionary algorithm NSGA.
    Methods are based on the Python libay Platypus:
        https://platypus.readthedocs.io/en/latest/index.html
    
    This class is used to define the optimization problem.
    Consequently different optimization methods can be applied to the defined problem.
    
    Methods
    -------
    evaluate
    simulation
    '''
    
    def __init__(self, 
                 pv_peak_power=None,
                 wt_nominal_power=None,
                 battery_capacity=None):

        ## Initialize Problem
        # Three decision variables, two objectives, and four constraints of objectives (top/bottom)
        super(system_optimisation, self).__init__(3,2,4)
        self.directions[0] = Problem.MINIMIZE
        self.directions[1] = Problem.MINIMIZE
        
        # Define the decision variables, Type of value: INTEGER and constraints
        int1 = Integer(1, 5000)           # PV peak Power
        int2 = Integer(1, 5000)           # WT nominal power
        int3 = Integer(1, 5000)           # Battery capacity
        self.types[:] = [int1, int2, int3]
        self.constraints[0] = ">=0"
        self.constraints[1] = "<=0"
        self.constraints[2] = ">=0"
        self.constraints[3] = "<=0"


    def evaluate(self, solution):
        '''
        Evaluation method is performed:
            Simulation method to run simulation and get objetive functions and its contraints       
        '''
        # Define decision variables
        self.pv_peak_power = solution.variables[0]
        self.wt_nominal_power = solution.variables[1]
        self.battery_capacity = solution.variables[2]
        
        # Call function to evaluate problem
        sim = self.simulation()
        
        # Get objective functions and constraints
        solution.objectives[:] = sim[0]
        solution.constraints[:] = sim[1]


    def simulation(self):
        '''
        Simulatoin method defines the evaluation function to provide the objective function.
        
        In this case it is the simulation:
            which needs to be defined with its parameter
            the objective functions to be used for the optimization
        
        '''
        
        ## Define simulation settings        
        # Simulation timestep in seconds
        timestep = 60*60
        # Simulation number of timestep
        simulation_steps = 24*365
         
        ## Create Simulation instance
        sim = Simulation(simulation_steps=simulation_steps,
                         timestep=timestep,
                         pv_peak_power=self.pv_peak_power,
                         wt_nominal_power=self.wt_nominal_power,
                         battery_capacity=self.battery_capacity)
        
        #Load timeseries irradiation data
        sim.env.meteo_irradiation.read_csv(file_name='data/env/SoDa_Cams_Radiation_h_2006-2016_Arusha.csv',
                                           start=0, 
                                           end=simulation_steps)
        #Load weather data
        sim.env.meteo_weather.read_csv(file_name='data/env/SoDa_MERRA2_Weather_h_2006-2016_Arusha.csv', 
                                       start=0, 
                                       end=simulation_steps)
        
        #Load load demand data
        sim.load.load_demand.read_csv(file_name='data/load/load_dummy_h.csv', 
                                      start=24, 
                                      end=48)
        
        ## Call Main Simulation method
        sim.simulate()
   
              
        ## Simulation evaluation
        ## Technical performance
        tech = Performance(simulation=sim, 
                           timestep=timestep)
        tech.calculate()
        # Get number of days with power cut offs
        DaysCutOff = tech.cut_off_day_number
       
        ## Economics
        eco_pv = Economics(sim.pv, 
                           sim.pv_replacement, 
                           timestep)
        eco_pv.calculate()
        
        eco_pv_charger = Economics(sim.pv_charger, 
                                sim.pv_charger_replacement, 
                                timestep)
        eco_pv_charger.calculate()
        
        eco_wt = Economics(sim.wt,
                           sim.wt_replacement,
                           timestep)
        eco_wt.calculate()
        
        eco_wt_charger = Economics(sim.wt_charger,
                                sim.wt_charger_replacement,
                                timestep)
        eco_wt_charger.calculate()
        
        eco_bms = Economics(sim.battery_management, 
                            sim.battery_management_replacement, 
                            timestep)
        eco_bms.calculate()
        eco_bat = Economics(sim.battery, 
                            sim.battery_replacement, 
                            timestep)
        eco_bat.calculate()
        
        #Sum of each component LCoE
        LCoE = (eco_pv.annuity_total_levelized_costs \
                + eco_pv_charger.annuity_total_levelized_costs \
                + eco_wt.annuity_total_levelized_costs \
                + eco_wt_charger.annuity_total_levelized_costs \
                + eco_bms.annuity_total_levelized_costs \
                + eco_bat.annuity_total_levelized_costs) \
                / ((sum(sim.load_power_demand)-sum(tech.loss_of_power_supply)) \
                   *(timestep/3600)/1000 / (simulation_steps*(timestep/3600)/8760))
        
        return [LCoE, DaysCutOff], [LCoE, LCoE-2, DaysCutOff, DaysCutOff-100]
        

## Initialize optimization problem
"""
# The final population could contain infeasible and dominated solutions
# if the number of function evaluations was insufficient (e.g. algorithm.Run(100)).
# In this case we would need to filter out the infeasible solutions:
# feasible_solutions = [s for s in algorithm.result if s.feasible]

# We could also get only the non-dominated solutions:
# nondominated_solutions = nondominated(algorithm.result)
"""

if __name__ == "__main__": 
    print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' Start')
    
    # Initialize the optimization problem with systen configuration (azimuth, inclination)
    problem = system_optimisation()
    
    with ProcessPoolEvaluator() as evaluator:   
        # instantiate the optimization algorithm
        algorithm = NSGAII(problem, population_size=100, evaluator=evaluator)
        # optimize the problem using alg_runs function evaluations
        algorithm.run(1000)

    
    ## Optimization output
    # Objective functions
    LCoE = np.array([s.objectives[0] for s in algorithm.result])
    DaysCutOff= np.array([s.objectives[1] for s in algorithm.result])
    
    # Decision variables
    pv_power = list()
    bat_capacity = list()
    for solution in algorithm.result:
        pv_power.append(problem.types[0].decode(solution.variables[0]))
        bat_capacity.append(problem.types[1].decode(solution.variables[1]))
        
    # Saving optimization results to csv file
    names=('LCoE', 'DaysCutOff', 'Ppv', 'Cbatt')
    optimization_results = pd.DataFrame({"LCoE":LCoE, 
                                         "DaysCutOff":DaysCutOff, 
                                         "PV_power":pv_power,   
                                         "Bat_capacity":bat_capacity})
    # Save results to csv
    optimization_results.to_csv('optimization_results.csv')    


    # Sample plotting
    fig = plt.figure()
    plt.scatter(LCoE, DaysCutOff, s=75, c=np.array(pv_power), alpha=.5)
    plt.xlabel('LCoE')
    plt.ylabel('DaysCutOff')
    plt.grid()
    cb=plt.colorbar()
    cb.set_label('PV power [$W_p$]')
    plt.show()