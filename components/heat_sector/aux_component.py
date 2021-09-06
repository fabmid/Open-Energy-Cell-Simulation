from simulatable import Simulatable
from serializable import Serializable

class Aux_Component(Serializable, Simulatable):
    '''
    Auxiliary heat component to support fluctuating energy technologies for heat supply.

    Attributes
    ----------
    Serializable: class. In order to load/save component parameters in json format
    Simulatable : class. In order to get time index of each Simulation step

    Methods
    -------

    Parameter
    ---------
    timestep : `int`
        [s] Simulation timestep in seconds.
    power_nominal : `int`
        [W] Nomial component power.
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Auxiliary component can define electric heater, heat pump or boiler.
    - No detailed modeling of component but amount of energy supplied and costs of supplied energy.
    - No partial load operation.
    '''

    def __init__(self,
                 timestep,
                 power_nominal,
                 file_path = None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)
        else:
            print('Attention: No json file for aux component model specified')
            self.specification = "Boiler"                                       # [-] Component specification
            self.specification_fuel = "Wood"                                    # [-] Fuel specification
            self.density_fluid = 1060                                           # [kg/m3] Density Fluid
            self.heat_capacity_fluid = 4182                                     # [J/(kg K)] Heat capacity Fluid
            self.efficiency = 0.90                                              # [1] Component efficiency at nominal power
            self.temperature_input_static = 313.15                              # [K] Fixed input temperature for static input temperature model
            self.temperature_output = 353.15                                    # [K] Fixed component output temperature
            self.temperature_minimum_heat_storage = 323.15                      # [K] Charge algorithm: Minimum heat storage temperature
            self.temperature_offset_heat_storage = 20                           # [K] Charge algorithm: Temperature offset above minimum heat storage for which aux comp stays ON

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # [s] Timestep
        self.timestep = timestep

        ## Basic parameters
        # Component nominal power in [W]
        self.power_nominal = power_nominal
        # Status parameter
        self.operation_mode = 'Off'
        # Volume flow rate [m3/s]
        self.volume_flow_rate = 0
        # Initial input and output temperature
        self.temperature_input = self.temperature_input_static
        self.temperature_output = self.temperature_output
        # Initial Storage temperature (check with initial values in heat storage class)
        self.temperature_heat_storage = 343.15


    def calculate(self):
        """Calculates all component performance parameters by calling implemented methods.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        power : `float`
            [W] Component power.
        volume_flow_rate : `float`
            [m3/s] Component volume flow dependent on operation mode and nominal power.
        energy_fuel : `float`
            [Wh] Component consumed fuel energy per timestep.

        Note
        ----
        - Charge algorithm consists of simple two point algorithm with static offset temperatures.
        """

        ## Aux component algorithm
        # Aux component is turned ON
        if self.operation_mode == 'Off' \
        and self.temperature_heat_storage <= self.temperature_minimum_heat_storage:
            # Set operation mode
            self.operation_mode = 'On'
            # Define volume flow rate [m3/s]
            self.volume_flow_rate = self.power_nominal / (self.density_fluid * \
                                    self.heat_capacity_fluid * (self.temperature_output-self.temperature_input))
            # Component power is set to nominal power
            self.power = self.power_nominal
            # Component fuel energy consumed
            self.energy_fuel = (self.power / self.efficiency) * (self.timestep / 3600)

        # Aux component stays ON
        elif self.operation_mode == 'On' and self.temperature_heat_storage \
        < (self.temperature_minimum_heat_storage + self.temperature_offset_heat_storage):
            # Set operation mode
            self.operation_mode = 'On'
            # Define volume flow rate [m3/s]
            self.volume_flow_rate = self.power_nominal / (self.density_fluid * \
                                    self.heat_capacity_fluid * (self.temperature_output-self.temperature_input))
            # Component power is set to nominal power
            self.power = self.power_nominal
            # Component fuel energy consumed
            self.energy_fuel = (self.power / self.efficiency) * (self.timestep / 3600)

        # Aux component is turned OFF
        elif self.operation_mode == 'On' and self.temperature_heat_storage \
        >= (self.temperature_minimum_heat_storage + self.temperature_offset_heat_storage):
            # Set operation mode to 'On'
            self.operation_mode = 'Off'
            # Define volume flow rate [m3/s]
            self.volume_flow_rate = 0.
            # Component power is set to 0
            self.power = 0.
            # Component fuel energy consumed
            self.energy_fuel = 0.

        # Aux component stays OFF
        else:
            # Set operation mode to 'On'
            self.operation_mode = 'Off'
            # Define volume flow rate [m3/s]
            self.volume_flow_rate = 0.
            # Component power is set to 0
            self.power = 0.
            # Component fuel energy consumed
            self.energy_fuel = 0.