import json

class Serializable:
    """Methods to make simulation serializable with json format, which makes it
    possible to automatically store and load components parameters in josn file.

    Parameters
    ----------
    file_path : `string`
        File path where to store/load json file.

    Returns
    -------
    None : `None`

    Note
    ----
    - Example of how to save battery parameters
        - anaconda prompt: navigate to base folder of simulation
        - open python
        - from serializable import Serializable
        - from component.battery import Battery
        - Serializable.save(Battery(None,None,None,None,"file path to battery.json"), "filepath to store new battery.json")
    - Attention json file is very sensible, manipulate it in spyder or suficated editor as atom.
    """

    def __init__(self,
                 file_path=None):

        self.file_path = file_path


    def load(self,
             file_path=None):
        """Load component parameter form specified json file to make it attributes of component class.

        Parameters
        ----------
        file_path : `string`
            File path where to load json file from.

        Returns
        -------
        None : `None`

        Note
        ----
        """

        # if no file_path is specified via load method it is taken from __init__method
        if not file_path:
            file_path = self.file_path

        # open json file from file_path
        with open(file_path, "r") as json_file:
            data = json.load(json_file)
            # Integrate content of json in component __init__ class
            self.__dict__ = data


    def save(self,
             file_path=None):
        """Save component parameter to json file from component class attributes.

        Parameters
        ----------
        file_path : `string`
            File path where to store json file.

        Returns
        -------
        None : `None`

        Note
        ----
        """

        # if no file_path is specified via load method it is taken from __init__method
        if not file_path:
            file_path = self.file_path

        # create json file in given file_path and save all parametrers given in __dict__ to it
        with open(file_path, "w") as json_file:
            # Filtering of unserializable objects in json
            obj_attributes = dict()
            for obj in self.__dict__:
                if not hasattr(self.__dict__[obj], '__dict__'):
                    obj_attributes[obj] = self.__dict__[obj]

            # final dump command with format parameter indent=4
            json.dump(obj_attributes, json_file, indent=4)