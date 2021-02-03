from datetime import datetime

from simulatable import Simulatable
from environment import Environment
from components.heat_sector.load_heat import Load_Heat
from components.heat_sector.solarthermal import Solarthermal
from components.heat_sector.aux_component import Aux_Component
from components.heat_sector.heat_storage import Heat_storage
from components.heat_sector.pipe import Pipe


class Simulation(Simulatable):
    """Central Simulation class, where energy system is defined and simulated.
    Extractable system power flows are defined here.

    Parameters
    ----------
    number collectors : `int`
        [1] Number of installed solarthermal collectors.
    st_orientation : `tuble of floats`
        [°] tuble of floats with collector oriantation azimuth and inclination.
    system_location : `tuble of floats`
        [°] tuble of floats with system location longitude and latitude.
    simulation_steps : `int`
        [1] Number of simulation steps.
    timestep: `int`
        [s] Simulation timestep in seconds.

    Note
    ----
    - Collector orientation - tuble of floats:
        - 1. tuble entry pv azimuth in degrees [°] (0°=north, 90°=east, 180°=south, 270°=west).
        - 2. tuble entry pv inclination in degrees [°]
    - System location coordinates:
        - 1. tuble entry system longitude in degrees [°]
        - 2. tuble entry system latitude in degrees [°]
    """

    def __init__(self,
                 number_collectors,
                 control_type,
                 storage_model,
                 storage_volume,
                 storage_number,
                 length_pipe,
                 aux_component_power,
                 system_location,
                 st_orientation,
                 simulation_steps,
                 timestep):

        ## Define simulation time parameters
        # Number of simulation timesteps
        self.simulation_steps = simulation_steps
        # [s] Simulation timestep
        self.timestep = timestep

        #%% Initialize classes
        # load class
        self.load_heat = Load_Heat(file_path='data/components/heat_load.json')

        # Environment class
        self.env = Environment(timestep=self.timestep,
                               system_orientation=st_orientation,
                               system_location=system_location)

        # Solarthermal class
        self.solarthermal = Solarthermal(timestep=self.timestep,
                                         number_collectors=number_collectors,
                                         env=self.env,
                                         control_type=control_type,
                                         file_path='data/components/solarthermal.json')
        # Pipe class
        self.pipe = Pipe(timestep=self.timestep,
                         length_pipe=length_pipe,
                         env=self.env,
                         input_link=self.solarthermal,
                         file_path='data/components/pipe.json')

        # Aux component
        self.aux_component = Aux_Component(timestep=self.timestep,
                                           power_nominal=aux_component_power,
                                           file_path='data/components/aux_component_boiler.json')

        # Heat storage class
        self.heat_storage = Heat_storage(storage_model=storage_model,
                                         storage_volume=storage_volume,
                                         storage_number=storage_number,
                                         timestep=self.timestep,
                                         env=self.env,
                                         input_link_1=self.pipe,
                                         input_link_2=self.aux_component,
                                         output_link=None,
                                         load_link=self.load_heat,
                                         file_path='data/components/heat_storage.json')

        ## Initialize Simulatable class and define needs_update initially to True
        self.needs_update = True

        Simulatable.__init__(self,
                             self.load_heat,
                             self.env,
                             self.solarthermal,
                             self.pipe,
                             self.aux_component,
                             self.heat_storage)


    #%% Call simulation method
    def simulate(self):
        '''
        Central simulation method, which :
            initializes all list containers to store simulation results
            iterates over all simulation timesteps and calls Simulatable.start/update/end()

        Parameters
        ----------
        None : `None`

        Returns
        -------
        All defined system parameters.
        '''
        ## Initialization of list containers to store simulation results
        # Timeindex
        self.timeindex = list()

        # Load demand
        self.load_heating_power_demand = list()
        self.load_heating_temperature_flow = list()
        self.load_heating_volume_flow_rate = list()
        self.load_hotwater_power_demand = list()
        self.load_hotwater_temperature_flow = list()
        self.load_hotwater_volume_flow_rate = list()

        #Solarthermal
        self.solarthermal_power_real = list()
        self.solarthermal_volume_flow_rate = list()
        self.solarthermal_efficiency_iam = list()
        self.solarthermal_temperature_input = list()
        self.solarthermal_temperature_output = list()
        self.solarthermal_temperature_mean = list()
        self.solarthermal_temperature_heat_storage = list()

        #Pipe
        self.pipe_power_real = list()
        self.pipe_power_to_storage = list()
        self.pipe_temperature_output = list()

        #Boiler
        self.aux_component_power = list()
        self.aux_component_volume_flow_rate = list()
        self.aux_component_temperature_input = list()
        self.aux_component_energy_fuel = list()

        # Heat storage
        self.heat_storage_temperature_mean = list()


        # As long as needs_update = True simulation takes place
        if self.needs_update:
            print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' Start')

            ## pvlib: irradiation and weather data
            self.env.load_data()

            ## Timeindex from irradiation data file
            time_index = self.env.time_index

            ## Call start method (inheret from Simulatable) to start simulation
            self.start()

            ## Iteration over all simulation steps
            for t in range(0, self.simulation_steps):
                ## Call update method to call calculation method and go one simulation step further
                self.update()

                ## Get heat storage temperature for solarthermal & aux component operation control
                self.solarthermal.temperature_heat_storage = self.heat_storage.temperature_mean
                self.aux_component.temperature_heat_storage = self.heat_storage.temperature_mean
                
                ## Get solarthermal input tempertaure from heat storage class
                # Should not be used in combination with a perfectly mixed heat storage
                #self.solarthermal.temperature_input = self.heat_storage.temperature_mean
                
                # Time index
                self.timeindex.append(time_index[t])

                # Load demand
                self.load_heating_power_demand.append(self.load_heat.heating_power)
                self.load_heating_temperature_flow.append(self.load_heat.heating_temperature_flow)
                self.load_heating_volume_flow_rate.append(self.load_heat.heating_volume_flow_rate)
                self.load_hotwater_power_demand.append(self.load_heat.hotwater_power)
                self.load_hotwater_temperature_flow.append(self.load_heat.hotwater_temperature_flow)
                self.load_hotwater_volume_flow_rate.append(self.load_heat.hotwater_volume_flow_rate)

                # Solarthermal collector
                self.solarthermal_volume_flow_rate.append(self.solarthermal.volume_flow_rate)
                self.solarthermal_power_real.append(self.solarthermal.power_real)
                self.solarthermal_efficiency_iam.append(self.solarthermal.efficiency_iam)
                self.solarthermal_temperature_input.append(self.solarthermal.temperature_input)
                self.solarthermal_temperature_output.append(self.solarthermal.temperature_output)
                self.solarthermal_temperature_mean.append(self.solarthermal.temperature_mean)
                self.solarthermal_temperature_heat_storage.append(self.solarthermal.temperature_heat_storage)

                #Pipe
                self.pipe_power_real.append(self.pipe.power_real)
                self.pipe_power_to_storage.append(self.pipe.power_to_storage)
                self.pipe_temperature_output.append(self.pipe.temperature_output)

                #Boiler
                self.aux_component_power.append(self.aux_component.power)
                self.aux_component_volume_flow_rate.append(self.aux_component.volume_flow_rate )
                self.aux_component_temperature_input.append(self.aux_component.temperature_input)
                self.aux_component_energy_fuel.append(self.aux_component.energy_fuel)

                # Heat storage
                self.heat_storage_temperature_mean.append(self.heat_storage.temperature_mean)

            ## Simulation over: set needs_update to false and call end method
            self.needs_update = False
            print(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), ' End')
            self.end()
