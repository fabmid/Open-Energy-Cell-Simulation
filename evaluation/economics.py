import numpy as np
import pandas as pd

from serializable import Serializable

class Economics(Serializable):
    '''
    Provides all relevant methods for the Levelized Costs of Energy calculation
    according to method cited in:
        T. Khatib, I. A. Ibrahim, and A. Mohamed, 
        ‘A review on sizing methodologies of photovoltaic array and storage battery in a standalone photovoltaic system’, 
        Energy Convers. Manag., vol. 120, pp. 430–448, Jul. 2016.
    
    Methods
    -------
    calculate
    
    capital_recovery_factor
    constant_escalation_levelisation_factor
    annuity_investment_costs
    annuity_operation_maintenance_costs
    annuity_replacement_costs
    annuity_residual_value
    annuity_total_levelized_costs
    '''
    
    def __init__(self, 
                 simulation,
                 performance,
                 file_path):
        '''
        Parameters
        ----------
        component : class. simulated component class
        component_replacement : list. List with timeindex of component replacement
            timeindex is dependent on set timestep
        timestep: int. Simulation timestep in seconds
        ''' 
        
        # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for economic model specified')

            self.name = "Economic_generic"
            self.timeframe = 10                                                 # [a] Timeframe of annuity calculation
            self.annual_percentage_rate= 0.05                                   # [-] Annual percentage rate/effektiver Jahreszins
            self.price_escalation_nominal= 0.03                                 # [-] Nominal price escalation rate
            self.grid_electricty_cost = 0.36                                    # [$] Electricty costs
            self.grid_feed_in_tarif = 0.10                                      # [$] electricty feed in tarif
            
        self.simulation = simulation
        self.performance = performance
        
        # Estract components list from simulation instance
        self.components = self.simulation.components 
        # Extract timestep from simulation instance
        self.timestep = self.simulation.timestep


    def calculate(self):
        '''
        Parameter
        ---------
        None
        '''
        
        self.results_replacements = {}
        self.results_cc = {}
        self.results_main = {}
        
        for i in range(0,len(self.components)):
            # Get one component
            self.component = self.components[i][0] # first entry of list is component
            # Get component id and class name for identification
            self.component_id = self.components[i][0].name
            self.name = type(self.components[i][0]).__name__
            # Get replacement array of component
            self.component_replacement = np.nonzero(self.components[i][1])[0] # second entry of list is replacement array
            # Check correctness of array!!

            ## Call economic methods
            # calculate economic parameter
            self.get_capital_recovery_factor()                   
            self.get_constant_escalation_levelisation_factor()
             
            # Calculation of all LCoE components
            self.get_annuity_investment_costs()
            self.get_annuity_operation_maintenance_costs()
            self.get_annuity_replacement_costs()
            self.get_annuity_residual_value()            
            self.get_annuity_total_levelized_costs()

            
            # Add results to dict
            self.results_replacements[self.component_id] = self.component_replacement
            self.results_cc[self.component_id] = self.component.investment_costs_specific \
                                                * self.component.size_nominal

            self.results_main[self.component_id] = [self.name,
                                                    self.component.size_nominal,
                                                    self.investment_costs,
                                                    self.operation_maintenance_costs,
                                                    self.replacement_costs,
                                                    self.residual_value,
                                                    self.annuity_investment_costs,
                                                    self.annuity_operation_maintenance_costs,
                                                    self.annuity_replacement_costs,
                                                    self.annuity_residual_value,
                                                    self.annuity_total_levelized_costs]

        # Calculate electricty costs for grid feed-OUT
        self.get_annuity_grid_feed_out_costs()
        # Calculate electricty costs for grid feed-IN
        self.get_annuity_grid_feed_in_costs()        

        # Summarizes overall results
        self.results = pd.DataFrame(data=self.results_main,
                                    index=['Comp_name','size_nom','cc','omc','repc','resv',
                                           'A_cc','A_omc','A_repc','A_resv','A_tlc'])
        
        # Calculate overall annuity of total levelized costs 
        self.annuity_total_levelized_costs_overall = self.results.loc['A_tlc'].sum() \
                                                    + self.annuity_grid_feed_out_costs \
                                                    - self.annuity_grid_feed_in_costs
    
    
        # Calculate Levelized Cost of Energy (Mischpreis bezogen auf kWh Strom und Wärme)
        self.levelized_cost_energy = self.annuity_total_levelized_costs_overall \
                                    / (self.performance.load_energy_el_kWh_a + self.performance.heat_pump_energy_el_consumed_kWh_a + self.performance.heat_pump_c_energy_el_consumed_kWh_a)
                                     
        #/ (self.performance.load_energy_el_kWh_a + self.performance.load_energy_heat_kWh_a)
                                     
       
    def get_capital_recovery_factor(self):
        '''
        Capital recovery factor
        
        Parameter
        ---------
        None
        '''
        self.capital_recovery_factor = (self.annual_percentage_rate* (1 + self.annual_percentage_rate)**self.timeframe) \
                                       / (((1 + self.annual_percentage_rate)**self.timeframe)-1)

    
    def get_constant_escalation_levelisation_factor(self):
        '''
        Constant Escalation Levelisation Factor - CELF (Nivelierungsfaktor)
        
        Parameter
        ---------
        None
        '''
        k = (1 + self.price_escalation_nominal) / (1 + self.annual_percentage_rate)
        self.constant_escalation_levelisation_factor = ((k*(1-k**self.timeframe)) \
                                                       / (1-k)) * self.capital_recovery_factor


    def get_annuity_grid_feed_out_costs(self):
        '''
        Annuity calculation of feed out grid costs
        
        Parameter
        ---------
        None

        Note
        ----
        - Nominal price escalation rate of 3%.
        '''
        # Calculate grid feed out energy [kWh]
        self.grid_feed_out_energy = sum(np.asarray([x for x in self.simulation.grid_power if x > 0]) \
                                                    * (self.timestep/3600)) / 1000
                                                   
        self.annuity_grid_feed_out_costs = (self.grid_feed_out_energy / self.timeframe) \
                                           * self.grid_electricty_cost \
                                           * self.constant_escalation_levelisation_factor


    def get_annuity_grid_feed_in_costs(self):
        '''
        Annuity calculation of feed out grid costs
        
        Parameter
        ---------
        None
        '''
        # Calculate grid feed out energy
        self.grid_feed_in_energy = abs(sum(np.asarray([x for x in self.simulation.grid_power if x < 0]) \
                                                    * (self.timestep/3600))) / 1000
        
        self.annuity_grid_feed_in_costs = self.grid_feed_in_energy \
                                           * self.grid_feed_in_tarif \
                                           * self.capital_recovery_factor
                                           

        
    def get_annuity_investment_costs(self):
        '''
        Annuity calculation of Investment Costs
        
        Parameter
        ---------
        None
        '''
                                        
        self.investment_costs = self.component.investment_costs_specific * self.component.size_nominal
                
        self.annuity_investment_costs = self.capital_recovery_factor * self.investment_costs

    
    def get_annuity_operation_maintenance_costs(self):
        '''
        Annuity calculation of Operation and Maintenance Costs
        
        Parameter
        ---------
        None
        
        Note
        ----
        - Nominal price escalation rate of 3%.
        '''
        self.operation_maintenance_costs = self.component.operation_maintenance_costs_specific \
                                           * self.component.size_nominal
        self.annuity_operation_maintenance_costs = self.operation_maintenance_costs \
                                                   * self.constant_escalation_levelisation_factor
                                                   
    
    def get_annuity_replacement_costs(self):
        '''
        Annuity calculation of Replacement Costs
        
        Parameter
        ---------
        None
        '''  
        # Define emtpty array for calculatiom of each replacement
        rc = np.zeros(len(self.component_replacement))
        
        # Cost calc for every replacement
        for k in range(0,len(self.component_replacement)):
            # Cost of each replacement with escalation rate r
            cc = (self.component.investment_costs_specific * self.component.size_nominal \
                  * (1 + self.price_escalation_nominal) \
                  **(self.component_replacement[k] / (365*24*(3600/self.timestep))))
            # Present value of replacement cost
            rc[k] = cc / (1+self.annual_percentage_rate) \
                    **(self.component_replacement[k] /(365*24*(3600/self.timestep)))
        
        # Annuity of present value
        self.replacement_costs = sum(rc)
        self.annuity_replacement_costs = self.capital_recovery_factor * self.replacement_costs

    
    def get_annuity_residual_value(self):
        '''
        Annuity calculation of Residual value
        
        Parameter
        ---------
        None
        '''  
        self.residual_value = ((1 - self.component.state_of_destruction) \
                                      * self.component.investment_costs_specific \
                                      * self.component.size_nominal)
        self.annuity_residual_value = self.residual_value \
                                      / ((1+self.annual_percentage_rate)**self.timeframe) \
                                      * self.capital_recovery_factor

    
    def get_annuity_total_levelized_costs(self):
        '''
        Annuity calculation of Total levelized costs
        
        Parameter
        ---------
        None
        '''  
        self.annuity_total_levelized_costs = self.annuity_investment_costs \
                                            + self.annuity_operation_maintenance_costs \
                                            + self.annuity_replacement_costs \
                                            - self.annuity_residual_value

    def print_economic_objectives(self):
        """
        
        """
        print('---------------------------------------------------------')
        print('Economic functions - Technical')
        print('---------------------------------------------------------')
        print('Levelized Cost of Energy [$/kWh]=', round(self.levelized_cost_energy, 6))
