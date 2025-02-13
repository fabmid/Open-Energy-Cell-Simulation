import pyomo.environ as pyo
from pyomo.common.timing import TicTocTimer, report_timing
from pyomo.opt import SolverStatus, TerminationCondition

class Optimizable:
    """Most central methods to make simulation "optimizable"...

    Parameters
    ----------
    **kwargs : `dict`
        Dict with all classes which shall be optimized (operational optimization) and further model parameters (timestep, simlation_steps)

    Returns
    -------
    None : `None`

    Note
    ----
    - Class needs to be initialized in system class
    """

    def __init__(self,
                 **kwargs):

        # Create empty list for all components (as simulatable class of them is not initialized with **kwargs)
        if not kwargs:
            self.kwargs = []

        # Get child lists and extract timestep and simulation_steps
        for key, value in kwargs.items():
            if key=='optimizables':
                self.childs_optimization = value

        ## Initialize Optimization model
        self.model = pyo.ConcreteModel()

        # Define set with timeperiods
        self.model.timeindex = pyo.RangeSet(self.simulation_steps)


    def data_prep(self, data):
        """
        Data preparation function to guerantee correct pyomo input data format

        Parameters
        ----------
        data : `list`
            [-] List, which holds pyomo input data

        Returns
        -------
        data_dict : `dict`
            [-] Dict, with index starting at 1, which holds list data

        Note
        ----
        - Function takes a list called data.
        - It stores list values in a dict, starting with index 1 (pyomo needs this structure)
        """

        # Define empty chunked data list
        data = data

        # Define index according to chunk size startign at 1
        index = list(range(1,len(data)+1))
        # Iterate over full simulation timeframe and chunk data
        for i in range(0, len(data)):
            # Append in every list index dictionary with chunked data and chunked index (every time startign at 1 again)
            return (dict(zip(index,data[i:i+len(data)])))


    def optimization_test(self):
         """
         Test method removes all components from childs list and from optimization calculation with capacity of 0!
         This enables also to set component capacity of 0 for a system of this component initialized

         Parameters
         ----------
         None : `None`

         Returns
         -------
         None : `None`

         Note
         ----
         - Removeable components:
             - Photovoltaic
             - Battery
             - Heat Pump
             - Thermal storage
             - Electrolyzer
             - Fuel cell
             - H2 storage
             - Wind turbine
         - Wäre auch noch erweiterbar auf: Heat Grid
         - If component is removed or not is checked with parameter size_nominal, used for economic calculation
         """

         # Calls method for all optimizable childs
         # empty list with components to be removed
         remove = list()

         # Iterate over all childs
         for child_opti in self.childs_optimization:

             if isinstance(child_opti, Optimizable):
                 # remove component from childs list in case it has capacity of 0!
                 try:
                     if child_opti.size_nominal == 0:
                         remove.append(child_opti)
                     else:
                         pass
                 # do nothing in case component is not sizeable or has capacity > 0!
                 except:
                     pass

         # Remove all components, which are in remove list
         self.childs_optimization =  [elem for elem in self.childs_optimization if elem not in remove]


    def optimization_get_block(self):
        """
        Pyomo: Get pyomo block construction of all model components

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Timeing reporting instance can be used to identify performance bottlenecks
        """

        # Calls method for all optimizable childs
        for child_opti in self.childs_optimization:

            if isinstance(child_opti, Optimizable):

                child_opti.optimization_get_block(self.model)


    def optimization_save_results(self):
        """
        Pyomo: Save results inside component classes

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Stores the optimized values in list containers inside component classes.
        """

        # Calls method for all optimizable childs
        for child_opti in self.childs_optimization:

            if isinstance(child_opti, Optimizable):

                child_opti.optimization_save_results()


    def optimization_run_model(self):
        """
        Pyomo: Just run and solve the constructed model.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Used solver and parameters could be defined in **kwargs and loaded from system data json.
        - Used solver needs to be installed independently!
        - Gurobi solver parameter description: https://www.gurobi.com/documentation/9.5/refman/parameter_descriptions.html:
            #self.solver.options["MIPGap"] = 0.005       # defaul: 0.0001
            #self.solver.options["Method"] = -1          # defaul: -1 Root relaxation algorithm choice
            #self.solver.options["MIPFocus"] = 1         # defaul: 0, 1 focus on good quality feasible solution, 2 focus on proving optimality, 3 best objective bound is moving very slowly
            #self.solver.options["Cuts"] = -1            # defaul: -1 level of aggressivenes of cutting plane strategy
            #self.solver.options["ScaleFlag"] = -1         # defaul: -1
            #self.solver.options["GURO_PAR_DUMP"] = 0    # default 0, in case 1 is set gurobi model, parameter, attr file is generated
            #self.solver.options["WorkLimit"] = 2000     # Work Limit until solver stops
        """

        ## solve the problem
        self.solver = pyo.SolverFactory(self.milp_solver)

        # If debug True solver timeing and main output is printed
        if self.milp_debug == "False":
            self.results = self.solver.solve(self.model, options=self.milp_solver_options)

        elif self.milp_debug == "True":
            self.results = self.solver.solve(self.model, options=self.milp_solver_options, report_timing=True, tee=True)

        else:
            print('Solver debug parameter not correctly set')

        # Check solver status
        if (self.results.solver.status == SolverStatus.warning or
            self.results.solver.status == SolverStatus.error):
                raise Exception('MILP is infeasible')
        else:
            pass