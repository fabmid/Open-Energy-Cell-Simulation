import numpy as np

from simulatable import Simulatable
from serializable import Serializable

class Fuelcell(Serializable, Simulatable):
    """ Relevant methods for the calculation of Fuel Cell performance.
    
    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    power_nominal : `int`
        [W] Installed fuel cell nominal power.
    storage_link : `class`
        Hydrogen storage class.
    file_path : `json`
        To load component parameters (optional).
        
    Note
    ----
    - Generic class, can be used for modeling of various fuel cell technologies.
    - Currently it reflects PEM fuel cells.   
    """
    
    def __init__(self,
                 timestep,
                 power_nominal,
                 storage_link,
                 file_path = None):
        
         # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for fuelcell model specified')
            
            self.specification = "PEM fuelcell"
            self.operation_point_optimum = 0.3                                  # [] Optimal operation point (max eff)       
            self.battery_soc_min = 0.6                                          # [] Minimal battery SoC, at which FC starts
            self.efficiency_el_a = 0.780853                                     # [] El. efficiency factor a
            self.efficiency_el_b = -0.76438                                     # [] El. efficiency factor b
            self.efficiency_el_c = -0.800804                                    # [] El. efficiency factor c        
            self.efficiency_el_d = -9.55679                                     # [] El. efficiency factor d 
            self.efficiency_el_e = 0.0                                          # [] El. efficiency factor e
            self.efficiency_th_a = 0.291707                                     # [] Th. efficiency factor a
            self.efficiency_th_b = 0.586111                                     # [] Th. efficiency factor b
            self.efficiency_th_c = -0.292195                                    # [] Th. efficiency factor c
            self.efficiency_th_d = -6.57437                                     # [] Th. efficiency factor d
            self.efficiency_th_e = 0.0                                          # [] Th. efficiency factor e                               
            self.end_of_life_operation = 108000000                              # [s] Enf of life in hours
            self.heating_value_kg = 33330                                       # [Wh/kg] Heating value of hydrogen   
            self.heating_value_Nm = 3000.0                                      # [Wh/Nm3] Heating value of hydrogen  
            self.investment_costs_a = 2.3879                                    # [] Economic function factor a
            self.investment_costs_b = -0.177                                    # [] Economic function factor b
            self.investment_costs_c = 0.0                                       # [] Economic function factor c    
            self.operation_maintenance_costs_share = 0.1                        # [1] Share of omc costs of cc
            
       # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate Serializable for serialization of component parameters
        Serializable.__init__(self)        
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # [s] Timestep
        self.timestep = timestep
        # [W] Nominal output power
        self.power_nominal = power_nominal
        
        # Integrate storage link
        self.storage_link = storage_link
  
        # Initialize initial paremeters
        self.power = 0
        self.power_to_battery = 0
        self.power_to_load = 0
        
        self.efficiency_el = 0
        self.efficeincy_th= 0
        self.power_hydrogen = 0
        self.heat_produced = 0
        
        self.operation  = 0
                
        ##Economic parameter
        # [W] Nominal power
        self.size_nominal = self.power_nominal
        # [€/W] Fuel cell specific investment costs (30% BOS included)
        self.investment_costs_specific = (1.3 * self.investment_costs_a \
                                        * (self.size_nominal/ 1000)**(self.investment_costs_b) \
                                        + self.investment_costs_c)
        # [€/W] Fuel cell specific operation and maintenance cost
        self.operation_maintenance_costs_specific = self.operation_maintenance_costs_share \
                                                    * self.investment_costs_specific     
 
#    def start(self):
#        """Simulatable method, sets time=0 at start of simulation.       
#        """
#
#    def end(self):
#        """Simulatable method, sets time=0 at end of simulation.    
#        """

    def calculate(self):
        """Simulatable method.
        Calculation is done inside energy management of electricty carrier.
        """        
        pass
    
                  
    def get_power(self):
        """ Calculates the fuel cell power and efficiencies.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        power_hydrogen : `float`
            [W] Fuel cell hydrogen power.
        heat_produced : `float`
            [W] Fuel cell produced heat.
        efficiency_el : `float`
            [1] Fuel cell electric efficiency.
        efficiency_th : `float`
            [1] Fuel cell thermal efficiency.
        
        Note
        ----
        Model is based on RLI Smooth model, compare [1]_.
            
        References
        ----------
        .. [1] https://github.com/rl-institut/smooth/blob/dev/smooth/components/component_pem_electrolyzer.py
        """
        ### System vom RLI 
        ### https://github.com/rl-institut/smooth/blob/dev/smooth/components/component_pem_electrolyzer.py           
        # The CHP an electrical efficiency and a thermal efficiency, both over
        # the load point, according to: Scholta, J. et.al. Small Scale PEM Fuel
        # Cells in Combined Heat/Power Co-generation. RCUB Afrodita.
        # http://afrodita.rcub.bg.ac.rs/~todorom/tutorials/rad24.html
     
        
        # Coefficients for efficiency function       
        # Efficiency
        if self.power != 0:
            self.efficiency_el = self.efficiency_el_a * np.exp(self.efficiency_el_b * (self.power/self.power_nominal)) \
                                 + self.efficiency_el_c * np.exp(self.efficiency_el_d * (self.power/self.power_nominal)) \
                                 + self.efficiency_el_e
                                 
            self.efficiency_th = self.efficiency_th_a * np.exp(self.efficiency_th_b * (self.power/self.power_nominal)) \
                                 + self.efficiency_th_c * np.exp(self.efficiency_th_d * (self.power/self.power_nominal)) \
                                 + self.efficiency_th_e
            # Hydrogen power consumed    
            self.power_hydrogen = - (self.power / self.efficiency_el)
            
            # Heat produced
            self.heat_produced = abs(self.power_hydrogen) * self.efficiency_th
            
        else:
            self.efficiency_el = 0
            self.efficiency_th = 0
            self.power_hydrogen = 0
            self.heat_produced = 0
            
             
    def get_state_of_destruction(self):
        """ Calculates the electrolyer state of destruction (SoD) and time of
        component replacement according to end of life criteria.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        state_of_destruction : `float`
            [1] Component state of destruction.
        replacement : `int`
            [s] Time of component replacement in seconds.
            
        Note
        ----
        - replacement_set stays at last replacement timestep for correct sod calculation after first replacement.
        """
        
        if self.power != 0:
            # Fuel cell in operation
            self.operation += 1
        else:
            pass
        
        self.state_of_destruction = (self.operation*self.timestep) / self.end_of_life_operation

        # In case component reached its end of life
        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.operation = 0
        else:
            self.replacement = 0
            