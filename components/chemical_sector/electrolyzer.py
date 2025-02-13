import numpy as np

from simulatable import Simulatable
from serializable import Serializable

class Electrolyzer(Serializable, Simulatable):
    """Relevant methods for the calculation of electrolyzer performance.
    
    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    power_nominal : `int`
        [W] Installed electrolyzer nominal power.
    storage_link : `class`
        Hydrogen storage class.
    file_path : `json`
        To load component parameters (optional).
        
    Note
    ----
    - Generic class, can be used for modeling of various electrolyzer technologies.
    - Currently it reflects PEM electrolyzer.
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
            print('Attention: No json file for battery model specified')

            self.name = "Electrolyzer"                                          # Component name
            self.specification = "PEM"                                                              
            self.partial_power_min = 0.0398                                     # [] Minimal partial load power 
            self.efficiency_nominal = 0.6947                                    # [1] Nominal efficiency
            self.efficiency_el_a = 0.732371                                     # [] El. efficiency factor a
            self.efficiency_el_b = -0.236654                                    # [] El. efficiency factor b
            self.efficiency_el_c = -1.57696                                     # [] El. efficiency factor c
            self.efficiency_el_d = -29.832                                      # [] El. efficiency factor d
            self.efficiency_el_e = 0.0                                          # [] El. efficiency factor e
            self.efficiency_th_a = 0.0876978                                    # [] Th. efficiency factor a
            self.efficiency_th_b = 0.329614                                     # [] Th. efficiency factor b    
            self.efficiency_th_c = -0.00676109                                  # [] Th. efficiency factor c
            self.compressor_spec_compression_energy = 1044.0                    # Specific compression energy (electrical energy needed per kg H2) [Wh/kg].      
            self.end_of_life_operation = 108000000                              # [s] End of life
            self.heating_value_kg = 33330.0                                     # [Wh/kg] Heating value of hydrogen   
            self.heating_value_Nm = 3000.0                                      # [Wh/Nm3] Heating value of hydrogen    
            self.investment_costs_a = 4.630687                                  # [] Economic function factor a
            self.investment_costs_b = -0.276                                    # [] Economic function factor b
            self.investment_costs_c = 0.0                                       # [] Economic function factor c
            self.operation_maintenance_costs_share = 0.05                       # [1] Share of omc costs of cc

            
        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate Serializable for serialization of component parameters
        Serializable.__init__(self)
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # [s] Timestep
        self.timestep = timestep
        # [W] Nominal input power
        self.power_nominal = power_nominal
        
        # Integrate hydrogen storage links
        self.storage_link = storage_link        
        
        # Initialize initial paremeters
        self.power = 0
        self.efficiency_el = 0
        self.efficiency_th = 0
        self.hydrogen_produced_power = 0
        self.hydrogen_produced_kg = 0
        self.hydrogen_produced_Nl = 0
        self.heat_produced = 0
        self.operation = 0

        ##Economic parameter
        # [W] Nominal power
        self.size_nominal = self.power_nominal
        # [$/W] Electrolyzer specific investment costs (30% BOS included)
        self.investment_costs_specific = (1.3 * self.investment_costs_a \
                                        * (self.size_nominal / 1000)**(self.investment_costs_b) \
                                        + self.investment_costs_c)
                                        
        # [€/W] Electrolyzer specific operation and maintenance cost
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
        """ Calculates the electrolyzer power and efficiencies.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        hydrogen_produced_power : `float`
            [W] Electrolyzer produced hydrogen.
        heat_produced : `float`
            [W] Electrolyzer produced heat.
        efficiency_el : `float`
            [1] Electrolyzer electric efficiency.
        efficiency_th : `float`
            [1] Electrolyzer thermal efficiency.
        
        Note
        ----
        Model is based on RLI Smooth model, compare [1]_.
            
        References
        ----------
        .. [1] https://github.com/rl-institut/smooth/blob/dev/smooth/components/component_pem_electrolyzer.py
        """
        
        # Efficiency
        if self.power != 0:
            self.efficiency_el = self.efficiency_el_a * np.exp(self.efficiency_el_b * (self.power/self.power_nominal)) \
                                 + self.efficiency_el_c * np.exp(self.efficiency_el_d * (self.power/self.power_nominal)) \
                                 + self.efficiency_el_e
            if self.efficiency_el < 0:
                self.efficiency_el = 0
                     
            self.efficiency_th = self.efficiency_th_a *(self.power/self.power_nominal)**2 \
                                 + self.efficiency_th_b * (self.power/self.power_nominal) \
                                 + self.efficiency_th_c
            if self.efficiency_th < 0:
                self.efficiency_th = 0        
                            
            self.hydrogen_produced_power = self.power * self.efficiency_el
            self.hydrogen_produced_kg = self.power * self.efficiency_el / self.heating_value_kg
            self.hydrogen_produced_Nl = self.power * self.efficiency_el / self.heating_value_Nm    
            self.heat_produced = self.power * self.efficiency_th
        
        else:
            self.efficiency_el = 0
            self.efficiency_th = 0
            self.hydrogen_produced_power = 0
            self.hydrogen_produced_kg = 0
            self.hydrogen_produced_Nl = 0  
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
            # Electrolyzer in operation
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