from simulatable import Simulatable

class Carrier_th(Simulatable):
    """Relevant methods of the power junction to compute all power input and
    output flows and the resulting battery power flow.

    Parameters
    ----------
    input_link_1 : `class`
        [-] Component 1 that provides input power to carrier
    input_link_2 : `class`
        [-] Component 2 that provides input power to carrier
    output_link_1 : `class`
        [-] Component 1 that provides output power to carrier
    output_link_2 : `class`
        [-] Component 2 that provides output power to carrier

    Note
    ----
    - Carrier can be electricity or heat carrier.
    - It's input and output flows are in each timestep balanced and itself has no storage cap.
    - Power flow sign is defined as carrier inputs (+) and outputs (-).
    """

    def __init__(self,
                 input_links,
                 output_links,
                 heat_pump_link,
                 heat_storage_link,
                 env):

        # Integrate simulatable class and connected component classes
        Simulatable.__init__(self)

        self.input_links = input_links
        self.output_links = output_links
        self.heat_pump = heat_pump_link
        self.heat_storage = heat_storage_link
      
        # Integrate environment class
        self.env = env
        
        # Heat exchanger (for FC and Ely waste heat integration)
        self.heat_exchanger_efficiency = 0.95
        
        # Initialize power flows
        self.power_0 = 0
        self.power_1 = 0
        self.power_2 = 0
        
        
    def calculate(self):
        """Energy Management system.
        
        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        
        Note
        ----
        - Calculates power difference of input and output power flows of carrier.
        - Runs storage, heat pump EMS according to implemented algorithm.
        """

        ## Energy Management System          
        # Summation of input links power
        self.input_links_power = 0
        for i in range(len(self.input_links)):
            self.input_links_power += self.input_links[i].heat_produced * self.heat_exchanger_efficiency
                
        # Summation of output links power
        self.output_links_power = 0
        for i in range(len(self.output_links)):
            self.output_links_power += self.output_links[i].power
          
        # Calculate resulting charge/discharge power
        self.power_0 = self.input_links_power + self.output_links_power
        
        ## Heat storage
        # Charge/discharge heat storage with resulting power and temperature limitation
        if self.heat_storage.temperature >= self.heat_storage.temperature_maximum:
            self.heat_storage.power = 0
        else:
            self.heat_storage.power = self.power_0
        # Include heat storage self discharge losses
        self.heat_storage.get_temperature_loss() 
        self.heat_storage.get_temperature()

        # Call Heat Pump EMS system
        # set heat pump to heating working mode (1)
        self.heat_pump.working_mode = 1
        self.ems_heat_pump()
     
        ## Heat storage
        self.power_1 = self.heat_pump.power_th
        # Charge/discharge heat storage with heat pump power
        self.heat_storage.power = self.power_1
        self.heat_storage.get_temperature()       


        # Check heat storage temperature level
        if self.heat_storage.temperature < self.heat_storage.temperature_minimum:
            # Electric heating
            # Load Heat storage with missing power (storage temperature level is maintained)
            self.power_2 = abs(self.power_1 + self.power_0)
            self.heat_storage.power = self.power_2
            self.heat_storage.get_temperature()
        
            # Add power to heat pump power el (direct heater power) (negative values)
            self.heat_pump.power -= self.power_2 # funzt noch nciht.
            self.heat_pump.speed_set = 'electric_heater'
            #print('electric heater')
            
    def ems_heat_pump(self):
        """
        Energy Management System for heat pump.       
        Calculates all heat pump performance parameters from implemented methods.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        None : `None`
        """
        
        # Get primary temperature (ambient conditions) [K]
        self.heat_pump.temperature_in_prim = (self.env.temperature_ambient[self.time])
        # Integrate icing losses
        if self.heat_pump.temperature_in_prim < self.heat_pump.temperature_threshold_icing:
            self.heat_pump.icing = self.heat_pump.factor_icing
        
        
        ## Heat pump runnign algorithm
        # Hp is switched On or stays on
        if self.heat_pump.operation_mode == 'Off' \
        and self.heat_storage.temperature < (self.heat_storage.temperature_target-self.heat_storage.temperature_hysterese) \
        or \
        self.heat_pump.operation_mode == 'On' \
        and self.heat_storage.temperature < self.heat_storage.temperature_target:

            # Set heat pump operation mode to 'On'
            self.heat_pump.operation_mode = 'On'

            # Thermal power calculation
            self.heat_pump.get_power_heating_mode()

            
        # HP is switsched off or stays off
        elif self.heat_pump.operation_mode == 'On' \
        and self.heat_storage.temperature >= self.heat_storage.temperature_target\
        or \
        self.heat_pump.operation_mode == 'Off' \
        and self.heat_storage.temperature >= (self.heat_storage.temperature_target-self.heat_storage.temperature_hysterese):
            
            # Set heat pump operation mode to 'Off'
            self.heat_pump.operation_mode = 'Off'

            # Thermal power calculation
            self.heat_pump.power_th = 0.
            # Electric power calculation
            self.heat_pump.power_el = 0. 
            self.heat_pump.power = 0. 
            # COP calculation
            self.heat_pump.cop = 0

        else:
            print('Heat pump hysterese status not defined!')