from simulatable import Simulatable
from serializable import Serializable

class Grid(Serializable, Simulatable):
    """Relevant methods to define a grid component.

    Parameters
    ----------
    None : `None`

    Note
    ----
    
    """


    def __init__(self,
                 file_path = None):

        # Read component parameters from json file
        if file_path:
            self.load(file_path)

        else:
            print('Attention: No json file for grid model specified')
            self.name = 'Grid_generic'

        # Integrate unique class instance identifier
        self.name = hex(id(self))         
        # Integrate Serializable for serialization of component parameters
        Serializable.__init__(self)   
        # Integrate simulatable class for simulation of component
        Simulatable.__init__(self)

        # Initialize grid power
        self.power = 0
    
    
    def start(self):
        """Simulatable method, sets time=0 at start of simulation.       
        """

    def end(self):
        """Simulatable method, sets time=0 at end of simulation.    
        """

    def calculate(self):
        """Simulatable method.
        Calculation is done inside energy management of electricty carrier.
        """        
