from simulatable import Simulatable
from serializable import Serializable

import numpy as np
import math
from scipy.interpolate import interp1d
from scipy.integrate import odeint

class Solarthermal(Serializable, Simulatable):
    """Relevant methods for the calculation of solarthermal collector performance.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    number_collectors : `int`
        [1] Number of installed solarthermal collectors.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed.
    control_type : `string`
        Solar pump control algorithm, either `no_control`, `two_point_control` or `pi_control`.
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Class can be implemented with heat storage
        - Advantage to better model solarthermal input temperature with heat storage.
    - Solarthermal input temperature:
        - Can be static value.
        - Or dynamic value from heat storage class (needs to be defined in simulation.py).
    - Differential equations can be used to compute collector output and mean temperature.
    - Three different solar pump algorithms implemented:
        - `no_control`, static input/mean/output temperature and no solar pump control, storage
          can always be charged till maximum temperature.
        - `two_point_control` and `pi_control`, dynamic/static input temperature and storage pump control.
    """

    def __init__(self,
                 timestep,
                 number_collectors,
                 env,
                 control_type,
                 file_path=None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for solarthermal model specified')
            # Parameters load json file
            self.collector_manufacturer = "Ritter Energie- und Umwelttechnik"   # [-] Name of collector manufacturer
            self.colector_type = "CPC collector Star 15/39"                     # [-] Name of collector type
            self.fluid_type = "water"                                           # [-] Type of solar fulid used
            self.area_collector_gross = 3.93                                    # [m2] Solar Gross Area (Bruttoflaeche)
            self.area_collector_aperture = 3.49                                 # [m2] Solar Apertur Area (Aperturflaeche)
            self.heat_capacity_effective = 9180                                 # [J/m2 K] Effective heat capacity based on apertur area
            self.efficiency_optical = 0.644                                     # [1] ST optical efficiency
            self.k0 = 0.749                                                     # [W/(m2 K)] Linear heat loss coefficient
            self.k1 = 0.005                                                     # [W/(m2 K)] Quadratic heat loss coefficient
            self.k_diff = 0.98                                                  # [] diffuser Einfallswinkelkorrekturfaktor
            self.aoi = [0,10,20,30,40,50,60,70,80,90]                           # [-] Incident Angle Modifier correction factors
            self.factor_transversal_list = [1.00,1.01,1.01,1.02,1.02,0.98,1.05,1.14,0.57,0.00]  # [-] Incident Angle Modifier correction factors
            self.factor_longitudinal_list = [1.00,1.00,1.00,0.99,0.98,0.95,0.89,0.76,0.38,0.00] # [-] Incident Angle Modifier correction factors
            self.density_fluid = 1060                                           # [kg/m3] Density Fluid Solar
            self.heat_capacity_fluid = 4182                                     # [J/(kg K)] Heat capacity Fluid Solar
            self.number_pipes = 21                                              # [-] Number of collector pipse
            self.mass_collector = 63                                            # [kg] Mass of collector
            self.volume_collector = 0.00319                                     # [m3] Volume of collector
            self.volume_flow_rate_specific = 25                                 # [l/m2ST/h] Solarthermal area specific volume flow rate
            self.temperature_input_static = 303.15                              # [K] No-Control: Solarthermal input temperature for static input temperature model
            self.temperature_mean_static = 323.15                               # [K] No-Control: Solarthermal mean temperature for static  model
            self.temperature_output_static = 343.15                             # [K] No-Control: Solarthermal output temperature for static model
            self.delta_temperature_top = 5                                      # [K] Two-Point-Control: Temperature difference between storage and collector to switch pump on
            self.delta_temperature_bottom = 2                                   # [K] Two-Point-Control: Temperature difference between storage and collector to switch pump off
            self.volume_flow_rate_pi = 0                                        # PI-Control: Initial volume flow rate
            self.pi_proportional_factor = 1.5e-07 * 100                         # PI-Control: Proportional factor
            self.pi_integration_time = 50                                       # PI-Control: Integration time
            self.pi_temperature_output_target = 273.15+70                       # [K] PI-control: Solarthermal target output temperature
            self.pi_control_value_min = 0                                       # [m3/2] PI-control: Value minimum volume flow rate
            self.pi_control_value_max = 1/3600                                  # [m3/2] PI-control: Value maximum volume flow rate

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate environment class
        self.env = env
        # [s] Timestep
        self.timestep = timestep

        ## Basic parameters
        self.number_collectors = number_collectors
        self.area_aperture = self.area_collector_aperture * self.number_collectors
        # Solar pump control type
        self.control_type = control_type

        ## Method: Solarthermal_efficiency_iam
        # Function fitting of Incident Angle Modifier correction factors
        self.fct_iam_transversal = interp1d(self.aoi, self.factor_transversal_list)
        self.fct_iam_longitudinal = interp1d(self.aoi, self.factor_longitudinal_list)

        ## Method: solarthermal_temperature_integrale - Initialize values
        # Initial input, output and mean collector temperature
        self.temperature_input = self.temperature_input_static
        self.temperature_output = self.temperature_input
        self.temperature_mean = self.temperature_input
        # Initial Storage temperature
        self.temperature_heat_storage = self.temperature_input

        # Initial volume flow rate of collector [m3/s]
        self.volume_flow_rate_base = (self.volume_flow_rate_specific * self.area_aperture) \
                                     / (3600 * 1000)
        self.volume_flow_rate = self.volume_flow_rate_base
        # Initial volume flow rate of collector [m3/s]
        self.volume_flow_rate_base = (self.volume_flow_rate_specific * self.area_aperture) \
                                     / (3600 * 1000)
        self.volume_flow_rate = self.volume_flow_rate_base
        # Status parameter
        self.operation_mode = 'Off'

        ## Define three solarthermal power carriers
        # [W] Theoretical collector power with solarthermal_power() method
        self.power_theo = 0
        # [W] Real collector power with volume flow rate and achieved collector temperature
        self.power_real = 0
        # [W] Collector power supplied to storage, dependent on storage temperature
        self.power_to_storage = 0


    def calculate(self):
        """Calculates all Solarthermal performance parameters by calling implemented methods

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `-`

        Note
        ----
        - According to specified control type implemented methods are called.
        """

        ## Integrate solar irradiation
        self.env_power = self.env.power[self.time]
        self.env_power_direct = self.env.power_poa_direct[self.time]
        self.env_power_diffuse = self.env.power_poa_diffuse[self.time]

        ## Integrate temperatures
        # ST input temperature, needs to be defined externally if dynamically
        self.temperature_input = self.temperature_input
        self.temperature_ambient = self.env.temperature_ambient[self.time]

        ## Integrate angles from env
        self.system_tilt = math.radians(self.env.system_tilt)
        self.sun_elevation = math.radians(self.env.sun_position_pvlib['elevation'][self.time])
        self.system_azimuth = math.radians(self.env.system_azimuth)
        self.sun_azimuth = math.radians(self.env.sun_position_pvlib['azimuth'][self.time])
        self.sun_aoi = math.radians(self.env.sun_aoi_pvlib[self.time])

        ## Control type: call calculation methods
        # No control
        if self.control_type == 'no_control':
            self.solarthermal_no_control()

        # 2 point control solar pump
        elif self.control_type == 'two_point_control':
            self.solarthermal_two_point_control()

        # PI control solar pump
        elif self.control_type == 'pi_control':
            self.solarthermal_pi_control()

        else:
            print('Solarthermal Pump control type needs to be specified!')


    def solarthermal_no_control(self):
        """Defines a static solarthermal algorithm with constant input, mean and output temperature.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        temperature_input : `float`
            [K] Collector input temperature, static.
        temperature_mean : `float`
            [K] Collector mean temperature, static.
        temperature_output : `float`
            [K] Collector output temperature, static.
        efficiency_iam : `float`
            [1] Collector efficiency with Incidence Angle Modifier, by calling method solarthermal_efficiency_iam().
        power_theo : `float`
            [W] Collector output power based on simple energy yield calc, by calling method solarthermal_power()
        power_real : `float`
            [W] Collector output power equals power_theo, due to static collector temperatures.
        volume_flow_rate: `float`
            [m3/s] Collector volume flow dependent on solarthermal power.

        Note
        ----
        - It assumes that heat storage can always be charged.
        - Can be used for simulations with hourly resolution.
        - Incidence Angle Modifier collector efficiency is used.
        """

        # Define static solarthermal temperatures
        self.tempertaure_input = self.temperature_input_static
        self.temperature_mean = self.temperature_mean_static
        self.temperature_output = self.temperature_output_static

        # Collector efficiency with Incidence Angle Modifier
        self.solarthermal_efficiency_iam()
        # Static model: Power calculation
        self.solarthermal_power(self.efficiency_iam)

        ## Calculate power dependent on volume flow rate and tempertature
        self.power_real = self.power_theo
        # Calculate voluem flow rate with assumed static output temperature
        self.volume_flow_rate = self.power_real / (self.density_fluid * self.heat_capacity_fluid \
                                * (self.temperature_output - self.temperature_input))


    def solarthermal_two_point_control(self):
        """Defines a simple Two-Point-Control algorithm of the solar pump.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        volume_flow_rate: `float`
            [m3/s] Collector volume flow, static to defined base rate.
        efficiency_iam : `float`
            [1] Collector efficiency with Incidence Angle Modifier, by calling method solarthermal_efficiency_iam().
        temperature_mean : `float`
            [K] Collector mean temperature, by calling method solarthermal_temperature_integrale().
        temperature_output : `float`
            [K] Collector output temperature, by calling method solarthermal_temperature_integrale().
        power_theo : `float`
            [W] Collector output power based on simple energy yield calc, by calling method solarthermal_power()
        power_real : `float`
            [W] Collector output power based on volume flow rate and temperature, dependent on heat storage status.

        Note
        ----
        - Method follows simple hysteresis curve with specified temperature delta.
        - Incidence Angle Modifier collector efficiency is used.
        """

        # Solar pump is switched on  OR Solar pump stays on
        if self.operation_mode == 'Off' \
        and self.temperature_output > (self.temperature_heat_storage + self.delta_temperature_top) \
        or \
        self.operation_mode == 'On' \
        and self.temperature_output >= (self.temperature_heat_storage + self.delta_temperature_bottom):

            # Set solarthermal operation mode to 'On'
            self.operation_mode = 'On'
            # Set solar pump flow rate [m3/s] ~ 25l/m2,st/h
            self.volume_flow_rate = self.volume_flow_rate_base

            # Collector efficiency with Incidence Angle Modifier
            self.solarthermal_efficiency_iam()
            # Integrale model: Mean solarthermal collector temperature
            self.solarthermal_temperature_integrale(self.efficiency_iam)
            # Static model: Power calculation
            self.solarthermal_power(self.efficiency_iam)

        # Solar pump is switsched off  OR  Solar pump stays off
        elif self.operation_mode == 'On' \
        and self.temperature_output < (self.temperature_heat_storage + self.delta_temperature_bottom)\
        or \
        self.operation_mode == 'Off' \
        and self.temperature_output <= (self.temperature_heat_storage + self.delta_temperature_top):

            # Set solarthermal operation mode to 'Off'
            self.operation_mode = 'Off'
            # Set solar pump flow rate [m3/s]
            self.volume_flow_rate = 0.
            # Solarthermal input temperature equals mean temperature of last timestep
            #self.temperature_input = self.temperature_mean

            # Collector efficiency with Incidence Angle Modifier
            self.solarthermal_efficiency_iam()
            # Integrale model: Mean solarthermal collector temperature
            self.solarthermal_temperature_integrale(self.efficiency_iam)
            # Static model: Power calculation with no solar irradiation
            self.env_power = 0
            self.solarthermal_power(self.efficiency_iam)

        # Solar pump stays off
        else:
            print('Solarthermal hysterese status not defined!')

        ## Calculate power dependent on volume flow rate adn tempertature
        self.power_real = self.volume_flow_rate * self.density_fluid * self.heat_capacity_fluid \
                        * (self.temperature_output - self.temperature_input)


    def solarthermal_pi_control(self):
        """Defines a PI control algorithm of the solar pump.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        efficiency_iam : `float`
            [1] Collector efficiency with Incidence Angle Modifier, by calling method solarthermal_efficiency_iam().
        temperature_mean : `float`
            [K] Collector mean temperature, by calling method solarthermal_temperature_integrale().
        temperature_output : `float`
            [K] Collector output temperature, by calling method solarthermal_temperature_integrale().
        power_theo : `float`
            [W] Collector output power based on simple energy yield calc, by calling method solarthermal_power()
        volume_flow_rate: `float`
            [m3/s] Collector volume flow, variable in order to achieve target output temperature.
        power_real : `float`
            [W] Collector output power based on volume flow rate and temperature, dependent on heat storage status.

        Note
        ----
        - Represents Matched Flow Control.
        - Incidence Angle Modifier collector efficiency is used.
        """

        # Get solarthermal output temperature of last timestep
        self.temperature_output_old = self.temperature_output

        # Collector efficiency with Incidence Angle Modifier
        self.solarthermal_efficiency_iam()
        # Integrale model: Mean solarthermal collector temperature
        self.solarthermal_temperature_integrale(self.efficiency_iam)
        # Static model: Power calculation
        self.solarthermal_power(self.efficiency_iam)

        # PI control algorithm
        e1 = self.pi_temperature_output_target - self.temperature_output_old
        e2 = self.pi_temperature_output_target - self.temperature_output
        self.volume_flow_rate_set = -self.pi_proportional_factor * (e2 - e1 \
                                    + 1/self.pi_integration_time * e2 * self.timestep) \
                                    + self.volume_flow_rate

        # Control value limitation (Stellgroessenbeschränkung)
        if self.volume_flow_rate_set <= self.pi_control_value_min: # minimum value
            self.volume_flow_rate = 0
        elif self.volume_flow_rate_set > self.pi_control_value_max: # maximum value
            self.volume_flow_rate = self.pi_control_value_max
        else:
            self.volume_flow_rate = self.volume_flow_rate_set

        # Define system status
        if self.volume_flow_rate > 0:
            self.operation_mode = 'On'
        else:
            self.operation_mode = 'Off'

        ## Calculate power dependent on volume flow rate and tempertature
        self.power_real = self.volume_flow_rate * self.density_fluid * self.heat_capacity_fluid \
                        * (self.temperature_output - self.temperature_input)


    def solarthermal_temperature_integrale(self, efficiency_used):
        """Calculates collector temperature distribution.

        Parameters
        ----------
        efficiency_used : `float`
            [1] Assumed collector efficiency, Incidence Angle Modifier or Optical efficiency.

        Returns
        -------
        temperature_mean : `float`
            [K] Collector mean temperature.
        temperature_output : `float`
            [K] Collector output temperatur.

        Note
        ----
        - Function is based on Integral Solarthermal collector model, 
          which is based on instationary, integral energy balance.
        - Mean collector temperature is based on assumption of linear temperatur distribution.
        - Calculation can be done for different collector efficiencies.
        """

        ## Define differential equation
        def solarthermal_temperature_integrale_fct(temperature_mean, t,
                                       temperature_ambient,
                                       area_aperture,
                                       heat_capacity_effective,
                                       efficiency,
                                       env_power,
                                       k0,k1,
                                       volume_flow_rate,
                                       density_fluid,
                                       heat_capacity_fluid,
                                       temperature_input):

            # Difference solarthermal mean collector and environmental temperature
            temperature_difference = temperature_mean - temperature_ambient

            # Differential equation
            dT_dt = 1 / (area_aperture * heat_capacity_effective) * (area_aperture \
                       * (efficiency * env_power - (k0*temperature_difference + k1*temperature_difference**2)) \
                       + volume_flow_rate * density_fluid * heat_capacity_fluid \
                       * (temperature_input - (2 * temperature_mean - temperature_input)))

            return dT_dt

        ## Call and solve differential equation
        # Time vector: defines the times for which equation shall be solved in seconds.
        self.time_vector = np.linspace(0,self.timestep,self.timestep)
        # Call numeric solver
        self.solarthermal_temperature_solve = odeint(solarthermal_temperature_integrale_fct,
                                                     self.temperature_mean,
                                                     self.time_vector,
                                                     args=(self.temperature_ambient,
                                                           self.area_aperture,
                                                           self.heat_capacity_effective,
                                                           efficiency_used,
                                                           self.env_power,
                                                           self.k0,
                                                           self.k1,
                                                           self.volume_flow_rate,
                                                           self.density_fluid,
                                                           self.heat_capacity_fluid,
                                                           self.temperature_input))

        # Get result of last time vector entry
        self.temperature_mean = self.solarthermal_temperature_solve[-1][0]
        self.temperature_output = 2 * self.temperature_mean - self.temperature_input


    def solarthermal_efficiency_iam(self):
        """Calculates collector efficiency with Incidence Angle Modifier.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        efficiency_iam : `float`
            [1] Collector efficiency with Incidence Angle Modifier.

        Note
        ----
        - Angle definitions: All angles must be defined in rad.
            - Sun_elevation: Sun elevation.
            - Sun_azimuth: Sun azimuth (N=0,O=90,S=180,W=270).
            - System_tilt: Collector tilt angle.
            - System_azimuth: Collector azimuth angle (N=0,O=90,S=180,W=270).
            - Sun_aoi: Sun incidence angle on tilted plane.
            - Theta_long: Longitudinal angle on tilted plane.
            - Theta_trans: Transversal angle on tilted plane.
        """

        # longitudinal angle
        self.theta_long = abs(math.degrees(self.system_tilt + math.atan(math.tan(math.radians(90) \
                          - self.sun_elevation) * math.cos(self.sun_azimuth - self.system_azimuth))))

        # Transversal angle
        self.theta_trans = abs(math.degrees(math.atan(math.cos(self.sun_elevation) \
                          * math.sin(self.sun_azimuth - self.system_azimuth) / math.cos(self.sun_aoi))))

        # longitudinal correction factors at longitudinal angle
        if self.theta_long <= 90:
            self.factor_longitudinal = self.fct_iam_longitudinal(self.theta_long)
        else:
            self.factor_longitudinal = 0
        # Transveral correction factors at transverall angle
        if self.theta_trans <= 90:
            self.factor_transversal = self.fct_iam_transversal(self.theta_trans)
        else:
            self.factor_transversal = 0

        # Angle correction factor for direct irradiation
        self.factor_dir = self.factor_longitudinal * self.factor_transversal

        # Calculate efficiency with Incidence Angle Modifier
        if (self.env_power_direct + self.env_power_diffuse) <= 0:
            self.efficiency_iam = self.efficiency_optical
        else:
            self.efficiency_iam = (self.efficiency_optical*(self.factor_dir*self.env_power_direct \
                                  + self.k_diff*self.env_power_diffuse)) \
                                  / (self.env_power_direct + self.env_power_diffuse)


    def solarthermal_power(self, efficiency_used):
        """Calculates collector output power with basic energy yield equation.

        Parameters
        ----------
        efficiency_used : `float`
            [1] Assumed collector efficiency, Incidence Angle Modifier or Optical efficiency.

        Returns
        -------
        power_theo : `float`
            [W] Collector theoretical output power.
        efficiency : `float`
            [W] Collector efficiency.

        Note
        ----
        - Static solarthermal collector power model based on simple energy balance.
        - Power can be calculated with static optical efficiency or iam efficiency.
        - Power represents theoretical power output, bcs. it is not dependent on 
          voluem flow rate, which is controlled by solar pump algorithm.
        - power theoretical can therefore overestimate collector output power.
        """

        # Difference solarthermal mean collector and environmental temperature
        self.temperature_difference = self.temperature_mean - self.temperature_ambient

        # Solarthermal collector theoretical power output
        self.power_theo = self.area_aperture * (efficiency_used * self.env_power \
                          - (self.k0 * self.temperature_difference + self.k1 * self.temperature_difference**2))

        if self.power_theo >= 0:
            self.power_theo = self.power_theo
        else:
            self.power_theo = 0