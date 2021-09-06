from simulatable import Simulatable
from serializable import Serializable

import numpy as np
import math
from scipy.integrate import odeint

class Pipe(Serializable, Simulatable):
    """Relevant methods to calculate heat loss and temperature in solarthermal system pipe.

    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    length_pipe : `int`
        [m] Lenght of pipe.
    environment : `class`
        To get access to solar irradiation, ambient temperature and windspeed.
    input_link: `class`
        Class of component which supplies input flow.
        Solarthermal output temperature == pipe input temperature.
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Pipe is connecting solarthermal collector with heat storage.
    - Differential equation is used to calculate pipe output temperature.
    - Is also used as delay element between collector and storage.
    """

    def __init__(self,
                 timestep,
                 length_pipe,
                 env,
                 input_link,
                 file_path=None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for solarthermal model specified')
            # Parameters load json file
            self.heat_capacity = 382                                            # [J/(kg K)] Heat capacity pipe
            self.density = 8940                                                 # [kg/m3] Density pipe
            self.wall_thickness = 0.00088                                       # [m] wall thickness pipe
            self.diameter_outer = 0.016                                         # [m] Outer diameter pipe
            self.heat_transfer_coef = 2                                         # [W/(m2 K)] Heat transfer coefficient pipe
            self.temperature_heating_room = 293.15                              # [K] Heating room temperature
            self.factor_mass = 1                                                # [1] Weighting factor mass
            self.density_fluid = 1060                                           # [kg/m3] Density fluid
            self.heat_capacity_fluid = 4182                                     # [J/(kg K)] Heat capacity fluid

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate environment class
        self.env = env
        # Integrate solarthermal class
        self.solarthermal = input_link
        # [s] Timestep
        self.timestep = timestep

        ## Basic parameters
        # [m] Length of pipe
        self.length = length_pipe
        # [m] Innen diameter pipe
        self.diameter_inner = self.diameter_outer - 2*self.wall_thickness
        # [kg] Mass of Pipe
        self.mass = (self.diameter_outer**2 - self.diameter_inner**2) \
                    * math.pi/4 * self.length * self.density
        # [kg] Mass of fluid in pipe
        self.mass_fluid = self.diameter_inner**2 * math.pi/4 \
                    * self.length * self.density_fluid

        # Initial pipe output temperature
        self.temperature_output = 298.15

        ## Define two pipe power carrier
        # [W] Real collector power with volume flow rate and achieved collector temperature
        self.power_real = 0
        # [W] Collector power supplied to storage, dependent on storage temperature
        self.power_to_storage = 0


    def calculate(self):
        """Calculates all pipe performance parameters by calling implemented methods.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        temperature_input : `float`
            [K] Solarthermal input temperature.
        temperature_pipe_input : `float`
            [K] Pipe input temperature (equals Soalrthermal output temperature).
        temperature_output : `float`
            [K] Pipe output temperature, by calling pipe_temperature_integrale().

        Note
        ----
        - temperture_input defines still solarthermal temperature input, in order to guarantee smooth solarthermal real pwoer determination.
        """
        ## Importing data from other classes
        # Solarthermal input temperature (for heat storage calculation, is needed for solarthermal power definition)
        self.temperature_input = self.solarthermal.temperature_input
        # Pipe input temperature ([K] Pipe input temperature = Solarthermal output power)
        self.temperature_pipe_input = self.solarthermal.temperature_output
        # Pipe volume flow rate
        self.volume_flow_rate = self.solarthermal.volume_flow_rate

        # Integrale model: Pipe
        self.pipe_temperature_integrale()

        ## Calculate power dependent on volume flow rate and tempertature
        self.power_real = self.volume_flow_rate * self.density_fluid * self.heat_capacity_fluid \
                        * (self.temperature_output - self.temperature_input)


    def pipe_temperature_integrale(self):
        """Calculates pipe temperature distribution.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        temperature_output : `float`
            [K] Pipe output temperature.

        Note
        ----
        - Integral energy balance over pipe between solarthermal collector and heat storage.
        """

        ## Define differential equation
        def pipe_temperature_integrale_fct(temperature_output,
                               t,
                               diameter_outer,
                               length,
                               mass,
                               heat_capacity,
                               temperature_input,
                               v_dot,
                               mass_fluid,
                               density_fluid,
                               heat_capacity_fluid,
                               heat_transfer_coef,
                               temperature_heating_room,
                               factor_mass):

            dT_dt = 1/((mass * heat_capacity + mass_fluid * heat_capacity_fluid) * factor_mass) \
                    * (v_dot * density_fluid * heat_capacity_fluid * (temperature_input - temperature_output) \
                    - heat_transfer_coef * diameter_outer * math.pi * length * (temperature_output - temperature_heating_room))

            return dT_dt

        ## Call and solve differential equation
        # Time vector: defines the times for which equation shall be solved in seconds.
        self.time_vector = np.linspace(0,self.timestep,self.timestep)
        # Call numeric solver
        self.pipe_temperature_solve = odeint(pipe_temperature_integrale_fct,
                                             self.temperature_output,
                                             self.time_vector,
                                             args=(self.diameter_outer,
                                                   self.length,
                                                   self.mass,
                                                   self.heat_capacity,
                                                   self.temperature_pipe_input,
                                                   self.volume_flow_rate,
                                                   self.mass_fluid,
                                                   self.density_fluid,
                                                   self.heat_capacity_fluid,
                                                   self.heat_transfer_coef,
                                                   self.temperature_heating_room,
                                                   self.factor_mass))

        self.temperature_output = self.pipe_temperature_solve[-1][0]