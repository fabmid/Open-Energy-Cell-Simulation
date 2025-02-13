import pyomo.environ as pyo
import pandas

import data_loader
from simulatable import Simulatable
from optimizable import Optimizable

class Load_Electricity(Simulatable, Optimizable):
    """Relevant methods to define the simulation load profile power.

    Parameters
    ----------
    None : `None`

    Note
    ----
    - Class data_loader is integrated and its method LoadDemand() to integrate csv load.
    - This method is called externally before the central method simulate() of the class simulation is called.

    """

    def __init__(self):

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)

        # Integrate load demand data_loader for csv load profile integration
        self.load_demand = data_loader.LoadDemand()
        self.electricity_load_data = None
        self.car_load_data = None


    def simulation_init(self):
        """Simulatable method.
        Initializes list containers to store simulation results.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        """

        ## List container to store results for all timesteps
        self.power_list = list()


    def simulation_calculate(self):
        """Extract power flow of load profile for each timestep in order to make class simulatable.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Load power values are also positive inside simulation!
        - Correct algebraic sign is considered in pyomo Bus constraint!
        """

        if not isinstance(self.electricity_load_data, pandas.core.series.Series):
            self.electricity_load_data = self.load_demand.get_electricity_profile()

        # [kW] Get electricity power for each timestep
        self.electricity_power = self.electricity_load_data.values[self.time % len(self.electricity_load_data)]

        if not isinstance(self.car_load_data, pandas.core.series.Series):
            self.car_load_data = self.load_demand.get_car_profile()

        # [kW] Get electricity power for each timestep
        self.car_power = self.car_load_data.values[self.time % len(self.car_load_data)]

        ## Combine electricity power as sum of appliances and car load
        self.power = self.electricity_power + self.car_power
        ## Save component status variables for all timesteps to list
        self.power_list.append(self.power)


    def optimization_get_block(self, model):
        """
        Pyomo: MILP electricity load block construction

        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`
        """

        # Central pyomo model
        self.model = model

        ## Electricity load block
        self.model.blk_electricity_load = pyo.Block()

        # Define parameters
        self.model.blk_electricity_load.power = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.power_list))


    def optimization_save_results(self):
        """
        Method to store optimization results

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        """

        pass