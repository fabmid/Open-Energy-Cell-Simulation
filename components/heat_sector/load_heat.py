import pyomo.environ as pyo
import pandas
import data_loader
from simulatable import Simulatable
from optimizable import Optimizable

class Load_Heat(Simulatable, Optimizable):
    """Relevant methods to define the simulation heat load profile.

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
        self.heating_load_data = None
        self.hotwater_load_data = None


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
        """Extracts power flow, flow temperature and volume flow rate of load profile
        for each timestep in order to make class simulatable.

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

        ## Heating load
        if not isinstance(self.heating_load_data, pandas.core.series.Series):
            self.heating_load_data = self.load_demand.get_heating_profile()

        # [kW] Get Load data and replicate it in case it is shorter than simulation time
        self.heating_power = self.heating_load_data.values[self.time % len(self.heating_load_data)]

        ## Hot Water load
        if not isinstance(self.hotwater_load_data, pandas.core.series.Series):
            self.hotwater_load_data = self.load_demand.get_hotwater_profile()

        # [kW] Get Load data and replicate it in case it is shorter than simulation time
        self.hotwater_power = self.hotwater_load_data.values[self.time % len(self.hotwater_load_data)]

        ## Combine heat power as sum of heating and hot drinkign water
        self.power = self.heating_power + self.hotwater_power
        ## Save component status variables for all timesteps to list
        self.power_list.append(self.power)


    def optimization_get_block(self, model):
        """
        Pyomo: MILP Heat Load block construction

        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`
        """

        # Central pyomo model
        self.model = model

        ## Heat load block
        self.model.blk_heat_load = pyo.Block()

        # Define parameters
        self.model.blk_heat_load.power = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.power_list))


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
