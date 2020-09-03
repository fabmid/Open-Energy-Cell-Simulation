from simulatable import Simulatable
from serializable import Serializable


class System_Controller(Serializable, Simulatable):
    '''
    Provides all relevant methods for the efficiency and aging calculation of power_components
    Model is based on method by Sauer and Schmid [Source]
    
    Methods
    -------
    calculate
    calculate_efficiency_output
    calculate_power_output
    calculate_efficiency_input
    calculate_power_input
    power_component_state_of_destruction
    
    Attributes calculated
    ---------------------
    power : float [W]. Output/Input power of powr component
    efficiency : float [1]. Efficiency of power component
    state_of_destruction: float [1]. State of destruction of power component
    '''
    
    def __init__(self, timestep, power_nominal, input_link, file_path = None):
        '''
        Parameters
        ----------
        timestep: int. Simulation timestep in seconds
        power_nominal : int. Nominal power of power component in watt [W]
        input_link : class. Class of component which supplies input power
        file_path : json file to load power component parameters
        '''
        
        # Read component parameters from json file
        if file_path:
            self.load(file_path)
            
        else:
            print('Attention: No json file for power component efficiency specified')
            
            self.specification = "Generic system controller"                    # [-] Specification of power component
            self.end_of_life_power_components = 315360000                       # [s] End of life time in seconds
            self.investment_costs_specific = 0.036                              # [$/Wp] Specific investment costs
            
        # Integrate Serializable for serialization of component parameters
        Serializable.__init__(self) # not needed !?
        # Integrate Simulatable class for time indexing
        Simulatable.__init__(self) # not needed !?
        # Integrate input power
        self.input_link = input_link
        # [s] Timestep 
        self.timestep = timestep

        
        ## Power model
        # Initialize power
        self.power = 0
        # set nominal power of power component
        self.power_nominal = power_nominal   
        
        ## Economic model
        # Nominal installed component size for economic calculation
        self.size_nominal = power_nominal        
           

    def calculate(self):
        ''' 
        Method calculates all power component parameter by calling implemented methods
        Decides weather input_power or output_power method is to be called
        
        Parameters
        ----------
        None
        '''
        
        input_link_power = self.input_link.power

        # Calculate the Power output or input
        if self.input_link.power >= 0:
            self.calculate_efficiency_output(input_link_power)
            self.calculate_power_output(input_link_power)
            
        if self.input_link.power < 0:
            self.calculate_efficiency_input(input_link_power)
            self.calculate_power_input(input_link_power)
        
        # Calculate State of Desctruction
        self.power_component_state_of_destruction()
        

    def calculate_efficiency_output (self, input_link_power):
        '''
        Power Component efficiency output model: 
        Method to calculate the efficiency dependent on Power Input eff(P_in)
        
        Parameters
        ----------
        None
        '''
        
        self.efficiency = 1


    def calculate_power_output (self, input_link_power):
        '''
        Power Component Power output model: 
        Method to calculate the Power output dependent on Power Input P_out(P_in)
        
        Parameters
        ----------
        None
        '''
                
        self.power = input_link_power * self.efficiency

        
    def calculate_efficiency_input (self, input_link_power):
        '''
        Power Component input model: 
        Method to calculate the efficiency dependent on Power Output Efficiency(P_out)
        Calculated power output is NEGATIVE but fuction can only handle Positive value
        Therefore first abs(), at the end -

        Parameters
        ----------
        None
        '''

        self.efficiency = 1


    def calculate_power_input (self, input_link_power):
        '''
        Power Component input model: 
        Method to calculate the Power input dependent on Power Output P_in(P_out)
        Calculated power output is NEGATIVE but fuction can only handle Positive value
        Therefore first abs(), at the end -

        Parameters
        ----------
        None
        '''
        
        self.power = input_link_power / self.efficiency
        

        
    def power_component_state_of_destruction(self):
        '''
        Power Component state of destruction model: Method to calculate SoD and time of component replacement
        according to end of life criteria
        
        Parameters
        ----------
        None
        '''
        # Calculate state of desctruction (end_of_life is given in seconds)
        self.state_of_destruction = self.time / (self.end_of_life_power_components/self.timestep)
        
        if self.state_of_destruction >= 1:
            self.replacement = self.time
            self.state_of_destruction = 0
            self.end_of_life_power_components = self.end_of_life_power_components + self.time
        else:
            self.replacement = 0