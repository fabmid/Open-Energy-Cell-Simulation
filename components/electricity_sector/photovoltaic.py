import pvlib
import pyomo.environ as pyo
import pandas as pd
import numpy as np

import data_loader
from simulatable import Simulatable
from serializable import Serializable
from optimizable import Optimizable

class Photovoltaic(Serializable, Simulatable, Optimizable):
    """Relevant methods for the calculation of photovoltaic performance.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    peak_power_arrays : `list of int`
        [kWp] List of Installed PV peak power values.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed data.
    file_name : `json`
        To load component parameters (optional).

    Note
    ----
    - Pvlib ModelChain is used where different model approaches can be applied
    - Json file is structured that PVWatts performance model can be applied
    - Model includes DC and AC model computation based on PVWAtts methods
    - PV system with different orientations can be modeled under the assumption of a single inverter connection
    - PV surface orientation
        - 1. Azimuth in degrees [°]. Panel azimuth from north (0°=north, 90°=east, 180°=south, 270°=west).
        - 2. Inclination in degrees [°]. Panel tilt from horizontal.
    - System location (tuble of floats)
        - 1. System longitude in degrees [°]. Positive east of prime meridian, negative west of prime meridian.
        - 2. System latitude in degrees [°]. Positive north of equator, negative south of equator.
    """

    def __init__(self,
                 timestep,
                 peak_power_arrays,
                 env,
                 file_path=None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for photovoltaic model specified')
            self.type = "PV"                                                    # [] Type of json component
            self.location_latitude = 52.5210                                    # [deg] Latitude degrees of considered system location
            self.location_longitude = 13.3929                                   # [deg] Longitude degrees of considered system location
            self.location_altitude = 36.0                                       # [m] Altitude of considered system location
            self.location_tz = 'UTC'                                            # Considered timezone
            self.module_type = 'glass_polymer'                                  # string - PV module type 'glass-glass' or glass-polymer'
            self.arrays_number = 3                                              # int -  Number of PV arrays with different orientation
            self.gamma_pdc = [-0.004,-0.004,-0.004]                             # list - [1/C] The temperature coefficient. Typically -0.002 to -0.005 (list length needs to equal arrays_number)
            self.surface_tilt = [35,35,35]                                      # list - List of array tilt orientation (list length needs to equal arrays_number)
            self.surface_azimuth = [90,180,270]                                 # list - List of array azimuth orientation (list length needs to equal arrays_number)
            self.albedo = 0.25                                                  # [] Albedo assumption
            self.transposition_model = 'isotropic'                              # string - default 'haydavies' – Passed to system.get_irradiance
            self.solar_position_method = 'nrel_numpy'                           # string default 'nrel_numpy' – Passed to location.get_solarposition.
            self.airmass_model = 'kastenyoung1989'                              # string - default 'kastenyoung1989' – Passed to location.get_airmass.
            self.dc_model = 'pvwatts'                                           # string - Valid strings are ‘sapm’, ‘desoto’, ‘cec’, ‘pvsyst’, ‘pvwatts’
            self.ac_model = 'pvwatts'                                           # string - Valid strings are ‘sandia’, ‘adr’, ‘pvwatts’
            self.aoi_model = 'no_loss'                                          # string - Valid strings are ‘physical’, ‘ashrae’, ‘sapm’, ‘martin_ruiz’, ‘no_loss’
            self.spectral_model = 'no_loss'                                     # string -  Valid strings are ‘sapm’, ‘first_solar’, ‘no_loss’
            self.temperature_model = 'sapm'                                     # string - Temperature model used in pvlib
            self.temperature_model_parameters = {'a': -3.47,
                                                 'b': -0.0594,
                                                 'deltaT': 3.0}                 # dict - Temperature model parameters
            self.dc_ohmic_model = "no_loss"                                     # string - Valid strings are ‘dc_ohms_from_percent’, ‘no_loss’
            self.losses_model = "pvwatts"                                       # string - Valid strings are 'no_loss or 'pvwatts'
            self.losses_parameters = {'soiling': 2.0,
                                      'shading': 3.0,
                                      'snow': 0.0,
                                      'mismatch': 2.0,
                                      'wiring': 2.0,
                                      'connections': 0.5,
                                      'lid':0.0,
                                      'nameplate_rating': 1.0,
                                      'age': 0.0,
                                      'availability':0.0}                       # dict - DC power losses in percentage
            self.inverter_model ='pvwatts'                                      # string - Inverter model used in pvlib
            self.inverter_efficiency_nom = 0.96                                 # [] Inverter nominal efficiency
            self.inverter_oversizing_ratio = 1.30                               # [1] Inverter oversizign ration  defined as ratio of (P_nom Inverter / P_nom PV plant)
            self.degradation_pv = 1.58154e-10                                   # [1/s] Photovoltaic degradation per second: deg_yearly=0.5% --> 0.005 / (8760*3600)
            self.end_of_life_condition = 0.8                                    # [-] Component end of life condition
            self.eco_no_systems = 1                                             # [1] The number of systems the peak power can be maximal allocated on, for sz3=5, sz4=128, sz5=72
                                                                                #  At this point all house roofs are listed also those where finally no system is mounted, this is indeicated in self.systems_orientation
            self.systems_orientation = {"east-west":5, "south":0, "no":0}       # [-] Orientation of PV systems in case of NH szenario (used in neighborhood class)
            self.capex_p1 = 1661.7                                              # [€$/kWp] capex: Parameter1 (gradient) for specific capex definition
            self.capex_p2 = -0.1210                                             # [€$/kWp] capex: Parameter2 (y-intercept) for specific capex definition
            self.subsidy_percentage_capex = 0.19                                           # Economic model: [%] Capex subsidy
            self.subsidy_limit = 1000000.0                                      # Economic model: [€/$] Max total capex subsidy
            self.opex_fix_p1 = 0.02                                             # [€$/kWp/a] opex-fixed:  % of capex
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
        # [kW] List of pv peak power of individual PV arrays
        self.peak_power_arrays = peak_power_arrays
        # [kW] Total installed PV peak power over all arrays
        self.peak_power_nominal = sum(self.peak_power_arrays)

        ## Aging model
        # [kW] Initialize Current PV peak power dependent on aging
        self.peak_power_current = self.peak_power_nominal
        # [kW] Initialize End-of-Life condition of PV module
        self.end_of_life = self.end_of_life_condition * self.peak_power_nominal

        ## Economic model
        # [kWp] Initialize Nominal power
        self.size_nominal = self.peak_power_nominal
        # Integrate data_loader for NH size distribution csv loading
        self.nh_loader = data_loader.NeighborhoodData()
        # Get the number of individual systems on which the peak power is installed
        # if attribute is not specified in json, set it to 1
        if not hasattr(self, 'eco_no_systems'):
            self.eco_no_systems = 1


    def simulation_init(self):
        """Simulatable method.
        Calulate all photovoltaic performance parameters by calling all
        methods based on pvlib.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`

        Note
        ----
        - Photovoltaic power/temperature is calculated using pvlib libary.
        - This libary computes parameters not step by step but all in one for env data.
        - Method is equal to environment class, where all env data is loaded all in one.
        - Other paranmeters are caculated step by step in the method photovoltaic.calculate().
        """
        
        ## List container to store simulation results for all timesteps
        self.power_dc_list = list()
        self.power_ac_list = list()
        self.power_list = list()
        self.temperature_list = list()
        self.degradation_factor_list = list()
        self.peak_power_current_list = list()
        self.state_of_destruction_list = list()
        self.replacement_list = list()

        ## Call pv lib methods to calculate all timesteps in batch
        self.get_location()
        self.get_system()
        self.run_model_chain()

        # Get economic parameters
        self.get_economic_parameters()


    def simulation_calculate(self):
        """Calculate and extracts all photovoltaic performance parameters from
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

        # Call Aging and State of Destruction functions
        self.get_aging()
        self.get_state_of_destruction()

        # Mean cell temperature of all PV arrays
        self.temperature = self.temperature_mc[self.time]
        # Total DC power of all arrays (inclduing degradation factor)
        self.power_dc = self.power_dc_mc[self.time] * self.degradation_factor
        # Total AC power of PV system (inclduing degradation factor)
        self.power = self.power_ac_mc[self.time] * self.degradation_factor

        ## Save component status variables for all timesteps to list
        self.power_dc_list.append(self.power_dc)
        self.power_list.append(self.power)
        self.temperature_list.append(self.temperature)
        self.degradation_factor_list.append(self.degradation_factor)
        self.peak_power_current_list.append(self.peak_power_current)
        self.state_of_destruction_list.append(self.state_of_destruction)
        self.replacement_list.append(self.replacement)


    def get_location(self):
        """
        Computes the latitude, longitude and timezone information of the pv system location.

        Returns
        -------
        None : `None`

        Note
        ----
        - https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.location.Location.html?highlight=location.location
        """
        
        # Define Location object
        self.location = pvlib.location.Location(latitude=self.location_latitude,
                                                longitude=self.location_longitude,
                                                tz=self.location_tz,
                                                altitude=self.location_altitude)


    def get_system(self):
        """
        Initializes a pvlib PVSystem object with the PV arrays and PV inverters.

        Returns
        -------
        None : `None`

        Note
        ----
        - https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.Array.html#pvlib.pvsystem.Array
        """
        
        # PV array definition
        self.module_parameters = list()
        self.mount = list()
        self.array = list()

        for i in range(0, self.arrays_number):
            # Define module parameters dict
            self.module_parameters.append({'pdc0': self.peak_power_arrays[i],
                                           'gamma_pdc': self.gamma_pdc[i]})

            # Mount definition of each array
            self.mount.append(pvlib.pvsystem.FixedMount(surface_tilt=self.system_tilt[i],
                                                        surface_azimuth=self.system_azimuth[i]))
            # Array definition of each array
            self.array.append(pvlib.pvsystem.Array(mount=self.mount[i],
                                                   albedo=self.albedo,
                                                   module_type=self.module_type,
                                                   module_parameters=self.module_parameters[i],
                                                   temperature_model_parameters=self.temperature_model_parameters))

        # Define PV inverter size (Oversizing can be considered)
        self.inverter_parameters = {'pdc0': (sum(self.peak_power_arrays) / self.inverter_oversizing_ratio),
                                    'eta_inv_nom': self.inverter_efficiency_nom}

        # Initialize PV system
        self.system = pvlib.pvsystem.PVSystem(arrays=self.array,
                                              inverter_parameters=self.inverter_parameters,
                                              losses_parameters=self.losses_parameters)


    def run_model_chain(self):
        """
        Runs the pvlib modelchain to compute the initialized PVSystem.

        Returns
        -------
        None : `None`

        Note
        ----
        - https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.modelchain.ModelChain.html#pvlib.modelchain.ModelChain

        """

        # Initialize model chain
        self.mc = pvlib.modelchain.ModelChain.with_pvwatts(system=self.system,
                                                           location=self.location,
                                                           transposition_model=self.transposition_model,
                                                           solar_position_method=self.solar_position_method,
                                                           airmass_model=self.airmass_model,
                                                           dc_model=self.dc_model,
                                                           ac_model=self.ac_model,
                                                           aoi_model=self.aoi_model,
                                                           spectral_model=self.spectral_model,
                                                           temperature_model=self.temperature_model,
                                                           dc_ohmic_model=self.dc_ohmic_model,
                                                           losses_model=self.losses_model)

        # Run mc model with solar environmental data
        self.mc.run_model(self.env.data_solar)

        # Extract main mc results
        if self.arrays_number > 1:
            self.temperature_mc = pd.concat(list(self.mc.results.cell_temperature), axis=1).mean(axis=1)
            self.power_dc_mc = pd.concat(list(self.mc.results.dc), axis=1).sum(axis=1)

        else:
            self.temperature_mc = self.mc.results.cell_temperature
            self.power_dc_mc = self.mc.results.dc

        self.power_ac_mc = self.mc.results.ac
        self.capacity_factor_ac = self.mc.results.ac / self.peak_power_nominal


    def optimization_get_block(self, model):
        """
        Pyomo: MILP PV block construction

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
        self.model.blk_pv = pyo.Block()

        # In case capacity is NOT 0, normal calculation
        if self.peak_power_nominal != 0:
            # Define parameters
            self.model.blk_pv.power = pyo.Param(self.model.timeindex, initialize=self.data_prep(self.power_list))
        # Incase capacity is 0 - no variables - only params=0!
        else:
            self.model.blk_pv.power = pyo.Param(self.model.timeindex, initialize=0)


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
        """Calculates photovoltaic power degradation and current peak power in Watt [W] assuming constant power degradation.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`
        """

        # PV power degradation
        self.peak_power_current = (1 - (self.degradation_pv * self.timestep)) * self.peak_power_current

        # Calculate degradation factor
        # Gives degradation not per timestep but for each timestep in comparision to nominal starting power)
        self.degradation_factor = (self.peak_power_current / self.peak_power_nominal)


    def get_state_of_destruction(self):
        """Calculate the photovoltaic state of destruction (SoD) and time of component replacement according to end of life criteria.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        - Replacement time is only set in timeseries array in case of a replacement, otherwise entry is 0.
        - In case of replacement current_peak_power is reset to nominal power.
        """

        # State of destruction (in case no component installed SoD=0)
        if self.peak_power_nominal != 0:
            self.state_of_destruction = (self.peak_power_nominal - self.peak_power_current) \
                                        / (self.peak_power_nominal -  self.end_of_life)
        else:
            self.state_of_destruction = 0

        # Store time index in list replacement in case end of life criteria is met
        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.peak_power_current = self.peak_power_nominal
        else:
            self.replacement = 0



    def get_economic_parameters(self):
        """Calculate the component specific capex and fixed opex for a neighborhood scenario where multiple systems are installed.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        None : `None`

        Note
        ----
        """
        # Calculate specific cost only if installed capacity is not 0!
        if self.peak_power_nominal != 0:
            # For single building scenarios - SB
            if self.eco_no_systems == 1:
                # [€$/kWp] Initialize specific capex
                self.capex_specific = (self.capex_p1 * (self.size_nominal/self.eco_no_systems)**self.capex_p2)
                # [€$/kWp] Initialize specific fixed opex
                self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
            # For neigborhood scenarios - NH
            else:
                # Get size distribution of PV systems in neighborhood
                self.size_nominal_distribution = self.nh_loader.get_pv_size_distribution()
                # Calculate specific capex distribution for different PV sizes
                self.capex_specific_distribution = [(self.capex_p1 * (self.size_nominal*j)**self.capex_p2) if j>0 else 0 for j in self.size_nominal_distribution]
                # [€$/kWp] Get NH specific capex as mean value of distribution
                self.capex_specific =  np.mean([i for i in self.capex_specific_distribution if i != 0])
                # [€$/kWp] Initialize specific fixed opex
                self.opex_fix_specific = (self.opex_fix_p1 * self.capex_specific)
        # No capex/opex fix in case of no installation
        else:
            self.capex_specific = 0
            self.opex_fix_specific = 0