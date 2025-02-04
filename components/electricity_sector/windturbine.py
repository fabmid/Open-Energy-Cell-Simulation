import pandas as pd
import windpowerlib as wplib
import pyomo.environ as pyo

from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable


class Windturbine(Serializable, Simulatable, Optimizable):
    """Relevant methods for the calculation of wind turbine performance.

    Parameters
    ----------
    timestep : 'int'
        [s] Simulation timestep in seconds.
    wt_number : `int`
        [-] Number of installed wind turbines.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed data.
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Model is based on windpowerlib v.0.2.0
    - Compare https://windpowerlib.readthedocs.io/en/v0.2.0/index.html
    - TurbineClusterModelChain is used with possibility to include WidFarm losses
    - Attention: Currently decision variable of comonent class is "number of wind turbines" as [float]:
        - Means it is also possible to install 1.5 turbines
    - Attention: not yet Unit test runnned
    """

    def __init__(self,
                 timestep,
                 wt_number,
                 env,
                 file_path=None):

        # Read component parameters of wind turbine from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for wind turbine model specified')
            self.specification = "Enercon E-82/2000"                             # wplib: [-] Wind turbine specification
            self.hub_height = 98                                                # wplib: [m] The height of the hub
            self.nominal_power = 2e6                                            # wplib: [W] Nominal turbine power
            self.power_curve_data = {"value": [0.0, 3.0e3, 25.0e3, 82.0e3, 174.0e3, 321.0e3, 532.0e3, 815.0e3, 1180.0e3, 1580.0e3, 1810.0e3, 1980.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3, 2050.0e3],
                                     "wind_speed": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0]},
            self.windfarm_efficiency = 0.8                                      # wplib: [] only needed in WindFarm if 'wake_losses_model' iN WindFarm objcet is set to 'wind_farm_efficiency'
            self.wake_losses_model =  'wind_farm_efficiency'                    # wplib: 'dena_mean' (default), None, 'wind_farm_efficiency' or name as 'knorr_extreme1' see fct. wake_losses.get_wind_efficiency_curve`
            self.smoothing = False                                              # wplib: False (default) or True
            self.block_width = 0.5                                              # wplib: default: 0.5 (only relevant of smooting=True)
            self.standard_deviation_method = 'Staffell_Pfenninger'              # wplib: 'turbulence_intensity' (default) or 'Staffell_Pfenninger' (only relevant of smooting=True)
            self.smoothing_order = 'wind_farm_power_curves'                     # wplib: 'wind_farm_power_curves' (default) or 'turbine_power_curves' (only relevant of smooting=True)
            self.wind_speed_model = 'logarithmic'                               # wplib: 'logarithmic' (default), 'hellman' or 'interpolation_extrapolation'
            self.density_model = 'ideal_gas'                                    # wplib: 'barometric' (default) or 'ideal_gas' or 'interpolation_extrapolation'
            self.temperature_model = 'linear_gradient'                          # wplib: 'linear_gradient' (def.) or 'interpolation_extrapolation'
            self.power_output_model = 'power_curve'                             # wplib: 'power_curve' (default) or 'power_coefficient_curve'
            self.density_correction = True                                      # wplib: False (default) or True
            self.obstacle_height = 0                                            # wplib: default: 0
            self.hellman_exp = None                                             # wplib: None (default) or None
            self.degradation = 5.0736e-10                                       # [1/s] Wind turbine degradation per second: deg_yearly=1.6%
            self.capex_p1 = 0.0                                                 # [€$/kW] capex: Parameter1 (gradient) for specific capex definition
            self.capex_p2 = 2516.8                                              # [€$/kW] capex: Parameter2 (y-intercept) for specific capex definition
            self.opex_fix_p1 = 0.0                                              # [€$/kW/a] opex-fixed: Parameter1 (gradient) for specific fixed opex costs
            self.opex_fix_p2 = 0.0                                              # [€$/kW/a] opex-fixed: Parameter2 (y-intercept) for specific fixed opex costs
            self.opex_var = 0.0                                                 # [€$/kWh] opex-variable: Specific variable opex dependent on generated energy


        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)

        # Integrate environment class
        self.env = env
        # [s] Timestep
        self.timestep = timestep

        ## Basic parameters
        # Number of turbines
        self.wt_number = wt_number
        # Nominal turbine power
        self.power_nominal_total = self.wt_number * self.nominal_power

        ## Wind turbine aging model
        # [kW] Current WT nominal power dependent on aging
        self.power_nominal_total_current = self.power_nominal_total
        # [kW] End-of-Life condition of wind turbine module
        self.end_of_life_wind_turbine = 0.7 * self.power_nominal_total

        ## Economic model
        # [kWp] Initialize Nominal power
        self.size_nominal = self.power_nominal_total
        if self.peak_power_nominal != 0:
            # [€$/kWp] Initialize specific capex
            self.capex_specific = (self.capex_p1 * self.size_nominal + self.capex_p2)
            # [€$/kWp] Initialize specific fixed opex
            self.opex_fix_specific = (self.opex_fix_p1 * self.size_nominal + self.opex_fix_p2)
        else:
            self.capex_specific = 0
            self.opex_fix_specific = 0


    def simulation_init(self):
        """Simulatable method, sets time=0 at start of simulation.
        Calulate all wind turbine performance parameters by calling all
        methods based on windpowerlib.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Wind turbine output power/class is calculated using windpowerlib libary.
        - Other paranmeters are caculated step by step in the method windturbine.calculate().
        """

        ## List container to store simulation results for all timesteps
        self.power_list = list()
        self.wind_speed_hub_list = list()
        self.density_hub_list = list()
        self.power_nominal_total_current_list = list()
        self.state_of_destruction_list = list()
        self.replacement_list = list()

        ## Call windpowerlib to calculate all timesteps in batch
        # Initializes wind turbine fleet
        self.get_system()

        # Define and run ModelChain
        self.run_model_chain()


    def simulation_calculate(self):
        """Calculate and extracts all wind turbine performance parameters from
        implemented methods.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Method mainly extracts parameters by calling implemented methods:
            - get_aging()
            - get_state_of_destruction()
        """

        # Aging and State of Destruction
        self.get_aging()
        self.get_state_of_destruction()

        # Power calculation with aging
        # Get total power output
        self.power = self.windfarm.power_output[self.time] / 1000               # transformation from W to kW
        # Get windspeed at hub height
        self.wind_speed_hub = self.windfarm.wind_speed_hub[self.time]
        # Get temperature at hub height
        self.temperature_hub = self.windfarm.temperature_hub[self.time]
        # Get density at hub height
        self.density_hub = self.windfarm.density_hub[self.time]

        ## Save component status variables for all timesteps to list
        self.power_list.append(self.power)
        self.wind_speed_hub_list.append(self.wind_speed_hub)
        self.density_hub_list.append(self.density_hub)
        self.power_nominal_total_current_list.append(self.power_nominal_total_current)
        self.state_of_destruction_list.append(self.state_of_destruction)
        self.replacement_list.append(self.replacement)


    def get_system(self):
        """Initializes Windfarm object.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - self.__dict__ should contain hub_height, nominal_power and power_curve with power curve values as DataFrame, which are to be defined in json file.
        - Following workflow is implemented for ModelChain definition:
            - Define Windturbine object with windturbine data: https://windpowerlib.readthedocs.io/en/stable/temp/windpowerlib.wind_turbine.WindTurbine.html
            - Define WindFarm object with wind fleet data: https://windpowerlib.readthedocs.io/en/stable/temp/windpowerlib.wind_farm.WindFarm.html#windpowerlib.wind_farm.WindFarm
        - See example implementation: https://windpowerlib.readthedocs.io/en/stable/examples.html
        """

        ## Prepare input data
        # Transfer power curve data into DataFrame
        self.power_curve = pd.DataFrame(self.power_curve_data)

        ## Initialize WindTurbine object
        # https://windpowerlib.readthedocs.io/en/stable/temp/windpowerlib.wind_turbine.WindTurbine.html
        # Specification of own wind turbine (Note: power curve values and nominal power have to be in Watt)
        self.turbine_data = {'nominal_power': self.nominal_power,
                             'hub_height': self.hub_height,
                             'power_curve': pd.DataFrame(data=self.power_curve_data)
                                }
        # Initilization of object
        self.turbine = wplib.WindTurbine(**self.turbine_data)

        ## Initialize WindFarm object
        # https://windpowerlib.readthedocs.io/en/stable/temp/windpowerlib.wind_farm.WindFarm.html#windpowerlib.wind_farm.WindFarm
        # Get WindFarm efficiency curves
        # https://windpowerlib.readthedocs.io/en/stable/temp/windpowerlib.wake_losses.get_wind_efficiency_curve.html
        self.windfarm_efficiency_curves = wplib.wake_losses.get_wind_efficiency_curve(curve_name='all')

        # Specification of wind farm data (possibility to contain wind farm efficiency)
        # wind turbine fleet is provided using the to_group function
        self.turbine_fleet_data = {'name': 'example_farm_2',
                                   'wind_turbine_fleet': [self.turbine.to_group(self.wt_number)], # 1 defines numbers of turbines in windfarm!
                                   'efficiency': self.windfarm_efficiency} # 'efficiency' only needed in WindFarm if wakeloss model is 'wind_farm_efficiency'

        # Initialization of object
        self.windfarm = wplib.WindFarm(**self.turbine_fleet_data)


    def run_model_chain(self):
        """Initialization of TurbineClusterModelChain to compute windpower

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - The TurbineClusterModelChain is a class that provides all necessary steps to calculate the power output of a wind farm or wind turbine cluster.
            - https://windpowerlib.readthedocs.io/en/stable/temp/windpowerlib.turbine_cluster_modelchain.TurbineClusterModelChain.html
        """

        # Define ModelChain data
        self.mc_data = {'wake_losses_model': self.wake_losses_model,
                        'smoothing': self.smoothing,
                        'block_width': self.block_width,
                        'standard_deviation_method': self.standard_deviation_method,
                        'smoothing_order': self.smoothing_order,
                        'wind_speed_model': self.wind_speed_model,
                        'density_model': self.density_model,
                        'temperature_model': self.temperature_model,
                        'power_output_model': self.power_output_model,
                        'density_correction': self.density_correction,
                        'obstacle_height': self.obstacle_height,
                        'hellman_exp': self.hellman_exp}


        # Initialize TurbineClusterModelChain with own specifications and use
        self.mc = wplib.TurbineClusterModelChain(self.windfarm,
                                                 **self.mc_data)

        ## Run_model method
        self.mc.run_model(self.env.wind_data)

        ## Get results and save them to farm object
        # write power output time series to WindTurbineCluster object
        self.windfarm.power_output = self.mc.power_output

        ## Subresults are not included in model chain result dict
        # Get Temperature at hub_height
        #https://windpowerlib.readthedocs.io/en/stable/temp/windpowerlib.modelchain.ModelChain.temperature_hub.html
        self.windfarm.temperature_hub = self.mc.temperature_hub(self.env.wind_data)

        # Get density at hub height
        #https://windpowerlib.readthedocs.io/en/stable/temp/windpowerlib.modelchain.ModelChain.density_hub.html
        self.windfarm.density_hub = self.mc.density_hub(self.env.wind_data)

        # Get wind speed at hub height
        #https://windpowerlib.readthedocs.io/en/stable/temp/windpowerlib.modelchain.ModelChain.wind_speed_hub.html
        self.windfarm.wind_speed_hub = self.mc.wind_speed_hub(self.env.wind_data)


    def optimization_get_block(self, model):
        """
        Pyomo: MILP Wind Turbine block construction

        Parameters
        ----------
        model : pyomo.model class instance (defined in optimizabe.py)

        Returns
        -------
        None : `None`
        """

        # Central pyomo model
        self.model = model

        ## PV block
        self.model.blk_wt = pyo.Block()

        # In case capacity is NOT 0, normal calculation
        if self.peak_power_nominal != 0:
            # Define parameters
            self.model.blk_wt.power = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.power_list))
         # Incase capacity=0 is installed - no variables - only params=0!
        else:
            self.model.blk_wt.power = pyo.Param(self.model.timeindex, initialize=0)


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


    def get_aging(self):
        """ Calculate wind turbine power degradation and current peak power in
        Watt [W] assuming constat power degradation.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        wind_turbine_power_nominal_current : `float`
            [Wp] Wind turbine current peak power in watt.
        """

        self.power_nominal_total_current = (1 - (self.degradation * self.timestep)) * self.power_nominal_total_current


    def get_state_of_destruction(self):
        """Calculate wind turbine state of destruction (SoD) and time of
        component replacement according to end of life criteria.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        state_of_destruction : `float`
            [1] Wind turbine State of destruction with SoD=1 representing a broken component.
        replacement : `int`
            [s] Time of wind turbine component replacement in seconds.

        Note
        ----
        - Replacement time is only set in timeseries array in case of a replacement, otherwise entry is 0.
        - In case of replacement current_power_nominal is reset to nominal power.
        """
        # State of destruction
        self.state_of_destruction = (self.power_nominal_total - self.power_nominal_total_current) \
                                    / (self.power_nominal_total - self.end_of_life_wind_turbine)

        # Store time index in list replacement in case end of life criteria is met
        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.power_nominal_total_current = self.power_nominal_total
        else:
            self.replacement = 0
