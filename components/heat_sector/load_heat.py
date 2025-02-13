import pandas
import data_loader
from simulatable import Simulatable
from serializable import Serializable

class Load_Heat(Serializable, Simulatable):
    """Relevant methods to define the simulation heat load profile.

    Parameters
    ----------
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Class data_loader is integrated and its method LoadDemand() to integrate csv load.
    - This method is called externally before the central method simulate() of the class simulation is called.
    - It defines heat load temperature and flow rate dependent on heat power demand.
    """

    def __init__(self,
                 file_path=None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for heat load model specified')
            self.specification = "heat_load"                                    # [-] Heat load specification
            self.density_fluid = 1060                                           # [kg/m3] Density fuild
            self.heat_capacity_fluid = 4182                                     # [J/(kg K)] Heat capacity fluid
            self.heating_temperature_flow_target = (273.15+60)                  # [K] Heating - Target Temperature of flow (Vorlauf)
            self.heating_temperature_flow = (273.15+60)                         # [K] Heating - Real Temperature of flow (Vorlauf), dependent on storage temperature
            self.heating_temperature_return = (273.15+35)                       # [K] Heating - Temperature of return (Rücklauf)
            self.hotwater_temperature_flow_target = (273.15+60)                 # [K] Hot Water - Target Temperature of flow (Vorlauf)
            self.hotwater_temperature_flow = (273.15+60)                        # [K] Hot Water - Real Temperature of flow (Vorlauf), dependent on storage temperature
            self.hotwater_temperature_return = (273.15+20)                      # [K] Hot Water - Temperature of return (Rücklauf)

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate load demand data_loader for csv load profile integration
        self.load_demand = data_loader.LoadDemand()

        #Initialize power of load profiles for heating and hot water
        self.heating_load_data = None
        self.heating_power = 0
        self.heating_volume_flow_rate = 0.

        self.hotwater_load_data = None
        self.hotwater_power = 0
        self.hotwater_volume_flow_rate = 0.


    def calculate(self):
        """Extracts power flow, flow temperature and volume flow rate of load profile
        for each timestep in order to make class simulatable.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        heating_power : `float`
            [W] Heating load power flow of timestep in watts.
        heating_volume_flow_rate : `float`
            [m3/s] Heating volume flow rate with given flow temperature and heating power.
        hotwater_power : `float`
            [W] Hot Water load power flow of timestep in watts.
        hotwater_volume_flow_rate : `float`
            [m3/s] Hotwater volume flow rate with given flow temperature and hotwater power.
        """

        ## Heating load
        if not isinstance(self.heating_load_data, pandas.core.series.Series):
            self.heating_load_data = self.load_demand.get_heating_profile()

        # Get Load data and replicate it in case it is shorter than simulation time
        self.heating_power = self.heating_load_data.values[self.time % len(self.heating_load_data)]
        # Calculate volume flow rate
        self.heating_volume_flow_rate = self.heating_power / (self.heat_capacity_fluid * self.density_fluid \
                                        * (self.heating_temperature_flow - self.heating_temperature_return))
        ## Hot Water load
        if not isinstance(self.hotwater_load_data, pandas.core.series.Series):
            self.hotwater_load_data = self.load_demand.get_hotwater_profile()

        # Get Load data and replicate it in case it is shorter than simulation time
        self.hotwater_power = self.hotwater_load_data.values[self.time % len(self.hotwater_load_data)]
        # Calculate volume flow rate
        self.hotwater_volume_flow_rate = self.hotwater_power / (self.heat_capacity_fluid * self.density_fluid \
                                         * (self.hotwater_temperature_flow - self.hotwater_temperature_return))

        
        ## !!! FAST AND DIRTY
        self.power = self.heating_power + self.hotwater_power
        
#    def re_calculate(self):
#        """Recalculates volume flow rate of load components with real flow temperature
#        coming from the heat storage.
#
#        Parameters
#        ----------
#        None : `None`
#
#        Returns
#        -------
#        heating_temperature_flow : `float`
#            [K] Heating load temperature of flow in Kelvin.
#        heating_volume_flow_rate : `float`
#            [m3/s] Heating load volume flow rate.
#        hotwater_temperature_flow : `float`
#            [K] Hot Water load temperature of flow in Kelvin.
#        hotwater_volume_flow_rate : `float`
#            [m3/s] Hot Water load volume flow rate.
#
#       Note
#        ----
#        - Can be called externally, e.g. from heat storage class.
#        """
#
#        ## Heating demand
#        # Define flow temperature of hot water heat load
#        self.heating_temperature_flow = self.heating_temperature_flow
#        # Re-calculate volume flow rate of hot water heat load [m3/s]
#        self.heating_volume_flow_rate = self.heating_power / (self.heat_capacity_fluid * self.density_fluid \
#                                         * (self.heating_temperature_flow - self.heating_temperature_return))
#
#        ## Hot water demand
#        # Define flow temperature of hot water heat load
#        self.hotwater_temperature_flow = self.hotwater_temperature_flow
#        # Re-calculate volume flow rate of hot water heat load [m3/s]
#        self.hotwater_volume_flow_rate = self.hotwater_power / (self.heat_capacity_fluid * self.density_fluid \
#                                         * (self.hotwater_temperature_flow - self.hotwater_temperature_return))
