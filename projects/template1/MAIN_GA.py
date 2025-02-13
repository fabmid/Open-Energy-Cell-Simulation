import numpy as np
import pandas as pd
import json
import sys

from platypus import Archive
from platypus import nondominated, unique
from platypus import NSGAII
from platypus import RandomGenerator, TournamentSelector
from platypus import ProcessPoolEvaluator

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

"""
Sample script to run GA with template1
    - GA:
        - default NSGA II
    - MILP:
        - default min(opex)
"""

#%% Archive
# Define LoggingArchive class
class LoggingArchive(Archive):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.log = []

    def add(self, solution):
        super().add(solution)
        self.log.append(solution)

#%% Main
if __name__ == "__main__":

    # Load config data
    config_list = ["data/cases/template1/config/main_config_template1.json"]

    ## Iteratie over all defined scenario configs
    for s in range(0, len(config_list)):

        # Initialize archive
        log_archive = LoggingArchive()

        # Load config
        with open(config_list[s], "r") as json_file:
            config = json.load(json_file)

        # Print scenario name
        print(config['name'])

        ## Adapt config for sample run
        config['ga_alg_runs'] = 10
        config['ga_pop_size'] = 10
        config['ga_processes'] = 2
        config["milp_solver_options"]["Threads"] = 3


        sys.path.insert(1, config["file_path_ga_problem"])
        from genetic_problem import Genetic_Problem

        # Initialize the optimization problem
        problem = Genetic_Problem(config)

        # Initialize the process pool
        with ProcessPoolEvaluator(processes=config['ga_processes']) as evaluator:
            # instantiate the optimization algorithm
            algorithm = NSGAII(problem,
                               population_size=config['ga_pop_size'],
                               generator=RandomGenerator(),
                               selector=TournamentSelector(2),
                               variator=None,
                               evaluator=evaluator,
                               archive=log_archive,
                               log_frequency=1)

            # optimize the problem using alg_runs function evaluations
            algorithm.run(config['ga_alg_runs'], callback = lambda a : print(a.nfe, unique(nondominated(algorithm.result))[0].objectives[:]))


        #%% Output
        # Define column names of solutions
        names = ['rank','annuity', 'grid_feed_out', 'pv', 'hp', 'tes_h', 'bat', 'ely', 'fc', 'h2']

        ## Get Feasible solutions
        feasible_solutions = [s for s in algorithm.result.log if s.feasible]
        feasible_solutions = nondominated(feasible_solutions)

        # create empty nd array to store results
        results = np.empty((len(feasible_solutions), int(len(config['ga_constraints'])/2 + 3)))

        # iterate over all population individuums
        for i, solution in enumerate(feasible_solutions):
            variables = list()
            objectives = list()
            rank = list()
            # Get Rank of solution
            try:
                rank.append(solution.rank)
            except:
                rank.append(0)
            # Get decision variable of solution
            for v in range(0, len(solution.variables)):
                variables.append(problem.types[v].decode(solution.variables[v]))
            # Get obj fct of solution
            for o in range(0, len(solution.objectives)):
                objectives.append(solution.objectives[o])
            # Combine all solutions in array (including dominated and non-dominated)
            results[i] = rank + objectives + variables

        # Convert results to df and save to csv
        results_df = pd.DataFrame(results, columns=names[0:results.shape[1]])
        # Get only non-dominated solutions
        results_nd_df = results_df[results_df['rank']==0]

        # Save results to csv
        file_path = config['file_path_results']
        results_nd_df.to_csv(file_path + config['name'] + '_nd.csv', sep=';')

        ## Unload case specific modules
        sys.modules.pop('genetic_problem')
        sys.modules.pop('milp_problem')