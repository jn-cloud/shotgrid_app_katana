from sgtk import Hook
from sgtk import TankError
from Katana import KatanaFile

class SceneOperation(Hook):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(self, operation, file_path, **kwargs):
        """
        Main hook entry point

        :operation: String
                    Scene operation to perform

        :file_path: String
                    File path to use if the operation
                    requires it (e.g. open)

        :returns:   Depends on operation:
                    'current_path' - Return the current scene
                                     file path as a String
                    all others     - None
        """

        if operation == "current_path":
            # return the current scene path
            if os.path.exists(os.path.dirname(file_path)):
                return file_path
            raise TankError("The active document must be saved!")

        elif operation == "open":
            KatanaFile.Load(file_path)

        elif operation == "save":
            if not os.path.exists(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))
            KatanaFile.Save(file_path)

        # if operation == "current_path":
        #     file_obj = katana.app.project.file
        #     if file_obj != None:
        #         return file_obj.fsName
        #     raise TankError("The active document must be saved!")

        # elif operation == "open":
        #     adobe.app.project.close(adobe.CloseOptions.DO_NOT_SAVE_CHANGES)
        #     adobe.app.open(adobe.File(file_path))

        # elif operation == "save":
        #     # save the current script
        #     adobe.app.project.save()

        return