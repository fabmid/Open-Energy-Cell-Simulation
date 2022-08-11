from simulatable import Simulatable
from serializable import Serializable

class Hydrogen_Storage(Serializable, Simulatable):
    """ Relevant methods for the calculation of hydrogen storage performance.
    
    Parameters
    ----------
    timestep : `int`
        [s] Simulation timestep in seconds.
    capacity_wh : `int`
        [Wh] Installed hydrogen capacity (chemical energy).
    file_path : `json`
        To load component parameters (optional).
        
    Note
    ----
    None
    """
    
    def __init__(self,
                 timestep,
                 capacity_wh,
                 file_path = None):
        
         # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for hydrogen storage model specified')
            self.specification = "Hydrogen Storage"
            self.state_of_charge_initial = 0.0                                  # [1] Initial storage SoC 
            self.heating_value_kg = 33330.0                                     # [Wh/kg] LHV hydrogen
            self.heating_value_Nm = 3000.0                                      # [Wh/Nm³] LHV hydrogen
            self.end_of_life = 946080000                                        # [s] End of life    
            self.investment_costs_specific = 0.0121                             # [$/Wh] Specific investment costs
            self.operation_maintenance_costs_share = 0.015                      # [1] Share of omc costs of cc

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate Serializable for serialization of component parameters
        Serializable.__init__(self)       
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)

       
        # [s] Timestep
        self.timestep = timestep
       
        # Storage capacity
        self.capacity_wh = capacity_wh
        self.capacity_kg = self.capacity_wh / self.heating_value_kg
        
        # Initialize initial paremeters
        self.state_of_charge = self.state_of_charge_initial
        # [W] Hydrogen charge or discharge power 
        self.power = 0
        
        ## Economic model
        # [Wh] Nominal capacity
        self.size_nominal = self.capacity_wh
        # [$/Wh] Storage specific investment costs
        self.investment_costs_specific = self.investment_costs_specific
        # [$/W] Fuel cell specific operation and maintenance cost
        self.operation_maintenance_costs_specific = self.operation_maintenance_costs_share \
                                                    * self.investment_costs_specific           
        ## Aging model
        self.replacement_set = 0
        

    def calculate(self):
        """Simulatable method.
        Calculation is done inside energy management of electricty carrier.
        """        
        pass


    def get_state_of_charge(self):
        """Calculates the hydrogen storage state of charge.

        Parameters
        ----------
        None : `-`

        Returns
        -------
        state_of_charge : `float`
            [1] Storage state of charge.

        Note
        ----
        - Model is based on simple energy balance using an off-line book-keeping method.
        - Considers no hydrogen losses.
        """
        
        # save soc of last timestep
        self.state_of_charge_old = self.state_of_charge
                
        # caculate soc of current timestep     
        self.state_of_charge = self.state_of_charge + (self.power / (self.capacity_wh) * (self.timestep/3600))
                                    
        self.state_of_charge = self.state_of_charge


             
    def get_state_of_destruction(self):
        """Calculates the component state of destruction (SoD) and time of
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

        # Calculate state of desctruction (end_of_life is given in seconds)
        self.state_of_destruction = (self.time - self.replacement_set) / (self.end_of_life/self.timestep)

        if self.state_of_destruction >= 1:
            self.replacement_set = self.time
            self.replacement = self.time
            self.state_of_destruction = 0
        else:
            self.replacement = 0
