import pandas as pd
import windpowerlib
from simulatable import Simulatable
from serializable import Serializable


class Wind_Turbine(Serializable, Simulatable):
    """Relevant methods for the calculation of wind turbine performance.
    
    Parameters
    ----------
    timestep : 'int'
        [s] Simulation timestep in seconds.
    peak_power : `int`
        [Wp] Installed wind turbine peak power.
    env : 
    
    file_path : `json`
        To load component parameters (optional).     
        
    Note
    ----
    - Model is based on windpowerlib v.0.2.0
    - Compare https://windpowerlib.readthedocs.io/en/v0.2.0/index.html
    """

    def __init__(self,
                 timestep,
                 peak_power,
                 env,
                 file_path=None):

        # Read component parameters of wind turbine from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for wind turbine model specified')
            self.turbine_type = "Enair 30PRO"                                   # [-] Wind turbine specification
            self.hub_height = 13                                                # [m] The height of the hub
            self.diameter = 3.8                                                 # [m] The diameter of the rotor
            self.nominal_power = 2500                                           # [m] Nominal turbine power
            self.power_curve_data = {"value": [0.0, 10.0, 100.0, 300.0, 1000.0, 1450.0, 1850.0, 2100.0, 2300.0, 2500.0, 2500.0, 2500.0, 2500.0],
                                     "wind_speed": [2.0, 3.0, 4.0, 5.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]}
            self.degradation = 5.0736e-10                                       # [1/s] Wind turbine degradation per second: deg_yearly=1.6%
            self.investment_costs_specific = 2.5168                             # [$/Wp] Wind turbine specific investment costs

        # Transfer power curve data into DataFrame
        self.power_curve = pd.DataFrame(self.power_curve_data)

        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # [s] Timestep
        self.timestep = timestep
        # Integrate environment class
        self.env = env

        ## Basic parameters  
        self.peak_power = peak_power
        # [W] Current PV peak power dependent on aging
        self.peak_power_current = self.peak_power

        ## Wind turbine aging model
        # [W] End-of-Life condition of wind turbine module
        self.end_of_life_wind_turbine = 0.7 * self.peak_power

        ## Wind turbine economic model
        # Nominal installed wind turbine size for economic calculation
        self.size_nominal = self.peak_power


    def load_data(self):
        """Calulates all wind turbine performance parameters by calling all
        methods based on windpowerlib.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        wind_turbine : :class:`~.wind_turbine.WindTurbine`
            [-] Photovoltaic cell temperature, by calling method 
            windturbine.initialize_wind_turbine()
        wind_power_output : `float`
            [W] Output power of wind turbine module, by calling method
            windturbine.power_output.
        Note
        ----
        - Wind turbine output power/class is calculated using windpowerlib libary.
        - Other paranmeters are caculated step by step in the method windturbine.calculate().
        """

        # Initializes wind turbine
        self.initialize_wind_turbine()

        # Calculates power output of wind turbine
        self.power_output()


    def calculate(self):
        """Calculates and extracts all wind turbine performance parameters from
        implemented methods.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        power : `float`
            [W] Wind turbine output power with time series 
        peak_power_current : `float`
            [W] Wind turbine current peak power assuming power degradation by
            implemented method wind_turbine_aging()
        state_of_destruction : `float`
            [-] Wind turbine state of destruction as fraction of current and
            nominal peak power.
        replacement : `float`
            [s] Time of replacement in case state_of_destruction equals 1.

        Note
        ----
        - Method mainly extracts parameters by calling implemented methods:
            - wind_turbine_aging()
            - wind_turbine_state_of_destruction()
        """

        # Power calculation with aging
        # Normalize power and multiplication with current peak power
        self.power = (self.wind_power_output.power_output[self.time] / self.nominal_power) * self.peak_power

        # Aging and State of Destruction
        self.wind_turbine_aging()
        self.wind_turbine_state_of_destruction()


    def initialize_wind_turbine(self):
        """Initializes own wind turbine.
        
        Parameters
        ----------  
        None : `None`

        Returns
        -------
        
        Note
        ----
        - self.__dict__ should contain hub_height, nominal_power and power_curve with power curve values as DataFrame
        - To be defined in json file.
        - Notes from windpowerlib:
            - Your wind turbine object needs to have a power coefficient or power curve. 
            - By default they are fetched from the oedb turbine library that is provided along with the windpowerlib. In that case turbine_type must be specified. 
            - You can also set the curves directly inside your json file.
        - Compare https://windpowerlib.readthedocs.io/en/v0.2.0/temp/windpowerlib.wind_turbine.WindTurbine.html
        """
        
        self.wind_turbine = windpowerlib.WindTurbine(**self.__dict__)


    def power_output(self):
        """Calculates power output of wind turbine by using windpowerlib Model Chain.
        
        Parameters
        ----------
        None : `None`

        Returns
        -------
        wind_speed_hub : `float`
            [m/s] Wind speed at rotor hub height.
        wind_power_output : `obj`
            [W] Output power of wind turbine module, by calling method
            windturbine.power_output.
            
        Note
        ----
        - ModelChain:
            - Needs initialized wind turbine object self.wind_turbine.
            - Currently density correction is not used.
            - Compare https://windpowerlib.readthedocs.io/en/v0.2.0/temp/windpowerlib.modelchain.ModelChain.html
            - Soure code: https://windpowerlib.readthedocs.io/en/stable/_modules/windpowerlib/modelchain.html#ModelChain.run_model
        - Run_model:
            - Compare https://windpowerlib.readthedocs.io/en/v0.2.0/temp/windpowerlib.modelchain.ModelChain.calculate_power_output.html#windpowerlib.modelchain.ModelChain.calculate_power_output
                
        """

        # Specifications for ModelChain setup
        modelchain_data = {'wind_speed_model': 'logarithmic',
                           'density_model': 'barometric',
                           'temperature_model': 'linear_gradient',
                           'power_output_model': 'power_curve',
                           'density_correction': True,
                           'obstacle_height': 0,
                           'hellman_exp': None}
        
        # Initialize ModelChain with initialized wind turbine parameters  
        modelChain = windpowerlib.modelchain.ModelChain(self.wind_turbine, **modelchain_data)
        
        # Run ModelChain
        self.wind_power_output = modelChain.run_model(self.env.wind_data)
        # Get wind speed at hub height
        self.wind_speed_hub = self.wind_power_output.wind_speed_hub(self.env.wind_data)
        
        # Alterantive: Run model steps mannualy (no object is returned but directly wind pwoer output)
        #self.wind_speed_hub = modelChain.wind_speed_hub(self.env.wind_data)
        #self.density_hub = modelChain.density_hub(self.env.wind_data)
        #self.wind_power_output = modelChain.calculate_power_output(self.wind_speed_hub,
        #                                                           self.density_hub)

        
    def wind_turbine_aging(self):
        """ Calculates wind turbine power degradation and current peak power in
        Watt [W] assuming constat power degradation.

        Parameters
        ----------
        None : `-`
        
        Returns
        -------
        wind_turbine_peak_power_current : `float`
            [Wp] Wind turbine current peak power in watt.
        """

        self.peak_power_current = (1 - (self.degradation * self.timestep)) * self.peak_power_current


    def wind_turbine_state_of_destruction(self):
        """Calculates wind turbine state of destruction (SoD) and time of
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
        - In case of replacement current_peak_power is reset to nominal power.
        """
        # State of destruction
        self.state_of_destruction = (self.peak_power - self.peak_power_current) \
                                    / (self.peak_power - self.end_of_life_wind_turbine)

        # Store time index in list replacement in case end of life criteria is met
        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.peak_power_current = self.peak_power
        else:
            self.replacement = 0
