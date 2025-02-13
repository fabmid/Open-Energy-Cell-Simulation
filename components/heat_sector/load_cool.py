import pandas
import data_loader
from simulatable import Simulatable
from serializable import Serializable

class Load_Cool(Serializable, Simulatable):
    """Relevant methods to define the simulation cooling load profile.

    Parameters
    ----------
    file_path : `json`
        To load component parameters (optional).

    Note
    ----
    - Class data_loader is integrated and its method LoadDemand() to integrate csv load.
    - This method is called externally before the central method simulate() of the class simulation is called.
    """

    def __init__(self):

        # Integrate unique class instance identifier
        self.name = hex(id(self))
        # Integrate simulatable class for time indexing
        Simulatable.__init__(self)
        # Integrate load demand data_loader for csv load profile integration
        self.load_demand = data_loader.LoadDemand()
        # Initialize power of load profile
        self.power = 0
        self.cooling_load_data = None
        



    def calculate(self):
        """Extracts power flow of cooling load profile for each timestep in order to make class simulatable.

        Parameters
        ----------
        None : `None`

        Returns
        -------
        power : `float`
            [W] Load power flow of timestep in watts.
        """

        if not isinstance(self.cooling_load_data, pandas.core.series.Series):
            self.cooling_load_data = self.load_demand.get_cooling_profile()

        self.power = self.cooling_load_data.values[self.time % len(self.cooling_load_data)]
        