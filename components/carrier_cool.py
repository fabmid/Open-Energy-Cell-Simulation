from simulatable import Simulatable

class Carrier_cool(Simulatable):
    """Relevant methods of the power junction to compute all power input and
    output flows and the resulting battery power flow.

    Parameters
    ----------
    input_links : `class`
        [-] Component 1 that provides input power to carrier
    output_links : `class`
        [-] Component 1 that provides output power to carrier
    """

    def __init__(self,
                 output_links,
                 heat_pump_link,
                 env):

        # Integrate simulatable class and connected component classes
        Simulatable.__init__(self)

        self.output_links = output_links
        self.heat_pump = heat_pump_link
        # Integrate environment class
        self.env = env
        

        
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
        - Runs heat pump EMS according to implemented simple cooling algorithm.
        """

        ## Energy Management System          
        # Summation of output links power
        self.output_links_power = 0
        for i in range(len(self.output_links)):
            self.output_links_power += self.output_links[i].power
          
        # Calculate resulting charge/discharge power
        self.power_0 = self.output_links_power

        # Call Heat Pump EMS system
        # Set heat pump working_mode to cooling mode (2)
        self.heat_pump.working_mode = 2

        # Get primary temperature (ambient conditions) [K]
        self.heat_pump.temperature_in_prim = (self.env.temperature_ambient[self.time])
        
        # Heat Pump cooling operation
        self.ems_heat_pump()
            
        
          
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
        
        ## Heat pump runnign algorithm
        # Heat pump operates only in case of cooling demand
        if self.output_links_power < 0:
            # Cooling power calculation
            self.heat_pump.get_power_cooling_mode()
            
            # Calculate power adjustment factor between cooling demand and heat pump cooling power
            self.heat_pump.power_adjustment = self.heat_pump.power_th / abs(self.output_links_power)
            # Adjust hp thermal output power to coolign demand
            self.heat_pump.power_th = self.heat_pump.power_th / self.heat_pump.power_adjustment
            self.heat_pump.power_el = self.heat_pump.power_el / self.heat_pump.power_adjustment
            self.heat_pump.power = self.heat_pump.power / self.heat_pump.power_adjustment 
            
        else:
            # Set heat pump operation mode to 'Off'
            self.heat_pump.operation_mode = 'Off'
            # Thermal power calculation
            self.heat_pump.power_th = 0.
            # Electric power calculation
            self.heat_pump.power_el = 0. 
            self.heat_pump.power = 0. 
            # EER calculation
            self.heat_pump.eer = 0
            
            self.heat_pump.power_adjustment = 0
                
        
            
