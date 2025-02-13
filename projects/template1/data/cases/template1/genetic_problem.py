from platypus import Problem, Real, Solution
from milp_problem import Milp_Problem

# %% Problem definition
class Genetic_Problem(Problem):
    """Class representing a GA problem.

    Attributes
    ----------
    nvars: int
        The number of decision variables
    nobjs: int
        The number of objectives.
    nconstrs: int
        The number of constraints.
    function: callable
        The function used to evaluate the problem.  If no function is given,
        it is expected that the evaluate method is overridden.
    types: FixedLengthArray of Type
        The type of each decision variable.  The type describes the bounds and
        encoding/decoding required for each decision variable.
    directions: FixedLengthArray of int
        The optimization direction of each objective, either MINIMIZE (-1) or
        MAXIMIZE (1)
    constraints: FixedLengthArray of Constraint
        Describes the types of constraints as an equality or inequality.  The
        default requires each constraint value to be 0.

    Note
    ----

    """

    def __init__(self, config):

        # Load parameter
        self.config = config
        # Initialize Problem
        # 7 decision variables, 2 objectives, and 1 constraint
        super().__init__(nvars=7, nobjs=2, nconstrs=1)

        # Minimization/Maximization of objective
        self.directions[0] = Problem.MINIMIZE
        self.directions[1] = Problem.MINIMIZE

        # Define the decision variables, Type of value: Real
        # Component comstraints _1 lower -2 upper constraint
        var1 = Real(self.config['ga_constraints']['pv_1'],
                    self.config['ga_constraints']['pv_2'])  # PV total peak Power
        var2 = Real(self.config['ga_constraints']['hp_1'],
                    self.config['ga_constraints']['hp_2'])  # HP peak Power_th
        var3 = Real(self.config['ga_constraints']['tes_h_1'],
                    self.config['ga_constraints']['tes_h_2'])  # TES volume
        var4 = Real(self.config['ga_constraints']['bat_1'],
                    self.config['ga_constraints']['bat_2'])  # Battery capacity
        var5 = Real(self.config['ga_constraints']['ely_1'],
                    self.config['ga_constraints']['ely_2'])  # Electrolyzer power
        var6 = Real(self.config['ga_constraints']['fc_1'],
                    self.config['ga_constraints']['fc_2'])  # Fuel cell power
        var7 = Real(self.config['ga_constraints']['h2_1'],
                    self.config['ga_constraints']['h2_2'])  # Hydrogen storage capacity

        self.types[:] = [var1, var2, var3, var4, var5, var6, var7]

        # Define constraint for H2 system
        self.constraints[0] = "==0"


    def evaluate(self, solution):
        """
        Evaluation method is performed:
            Simulation and MILP methods to get objective functions

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        # Get decision variable results and store in array
        res_vars = solution.variables

        # Initialize system with MILP
        sys = Milp_Problem(res_vars, self.config)

        # MILP is feasible
        try:
            # Call Main Simulation method (non-dispatchables)
            sys.simulate_non_dispatchables()
            # Call Optimization model
            sys.optimize_operation()
            # Call Main Simulation method (dispatchables)
            sys.simulate_dispatchables()
            # Call economic evaluation
            sys.calculate_economics()
            # Call performance evaluation
            sys.calculate_performance()

            # Get objective function results
            annuity_total = sys.eco.annuity_total
            #print(annuity_total)
            grid_feed_out_energy = sys.grid_feed_out_energy
            #print(grid_feed_out_energy)
            solution.objectives[:] = [annuity_total, grid_feed_out_energy]

        # MILP is infeasible
        except (Exception, ValueError, AttributeError) as e:
            print("An error occurred:", e)
            # Get objective function results (set bad obj values in case MILP is infeasible)
            solution.objectives[:] = [10000000000, 1000000000]

        # Add constraint for H2 system (if single H2 component is below min component size)
        if (solution.variables[4] < self.config['h2_min_sizes'][0]
            or solution.variables[5] < self.config['h2_min_sizes'][1]
            or solution.variables[6] < self.config['h2_min_sizes'][2]):
            solution.constraints[0] = (solution.variables[4] + solution.variables[5] + solution.variables[6])
        else:
            solution.constraints[0] = 0


class Generate_Population():
    """
    Generates a initial population with provided variable data
    Objective function and feasible indicator are not defined.

    Parameters
    ----------
    problem : class
        To define GA problem based on platypus
    config : dic
        Dic with all config information
    data_population : -
        Initial population for GA

    Returns
    -------
    None : `None`

    Note
    ----
    """

    def __init__(self,
                 problem,
                 config,
                 data_population):

        # Include argumnets
        self.problem = problem
        self.config = config
        self.data_population = data_population


    def get_population(self):
        """
        Get initial population based on config definition.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        """

        ## Initialize population
        # Create empty container for initial population - platypus Solution object
        self.population_initial = [Solution(self.problem) for i in range(self.config['ga_pop_size'])]

        # Iterate over all population inidividuals
        lst_pop = list()
        for i in range(self.config['ga_pop_size']):
            # Iterate over all variables of individuals
            lst_var = list()
            for x in range(0, len(self.problem.types)):
                # Append initial guess for all variables of individuum
                lst_var.append(self.problem.types[x].encode(self.data_population.iloc[i,x]))
            # Append all individum guesses to population guess
            lst_pop.append(lst_var)

        # Include guessed population into platypus Solution.Variable object
        for i in range(self.config['ga_pop_size']):
            self.population_initial[i].variables = lst_pop[i]

        return(self.population_initial)