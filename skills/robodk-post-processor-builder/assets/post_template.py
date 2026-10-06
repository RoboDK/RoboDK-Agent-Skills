# Copyright 2015 - RoboDK Global, SLU - https://robodk.com/
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ----------------------------------------------------
# This file is a POST PROCESSOR for Robot Offline Programming to generate programs
#
# To edit/test this POST PROCESSOR script file:
# Select "Program"->"Add/Edit Post Processor", then select your post or create a new one.
# You can edit this file using any text editor or Python editor. Using a Python editor allows to quickly evaluate a sample program at the end of this file.
# Python should be automatically installed with RoboDK
#
# You can also edit the POST PROCESSOR manually:
#    1- Open the *.py file with Python IDLE (right click -> Edit with IDLE)
#    2- Make the necessary changes
#    3- Run the file to open Python Shell: Run -> Run module (F5 by default)
#    4- The "test_post()" function is called automatically
# Alternatively, you can edit this file using a text editor and run it with Python
#
# To use a POST PROCESSOR file you must place the *.py file in "C:/RoboDK/Posts/"
# To select one POST PROCESSOR for your robot in RoboDK you must follow these steps:
#    1- Open the robot panel (double click a robot)
#    2- Select "Parameters"
#    3- Select "Unlock advanced options"
#    4- Select your post as the file name in the "Robot brand" box
#
# To delete an existing POST PROCESSOR script, simply delete this file (.py file)
#
# ----------------------------------------------------
# More information about RoboDK Post Processors and Offline Programming here:
#     https://robodk.com/help#PostProcessor
#     https://robodk.com/doc/en/PythonAPI/postprocessor.html
# ----------------------------------------------------

# ----------------------------------------------------
# Description
# (1-2 lines description of what this post generates)
#
# Supported Controllers
# (comma separated values with the controllers supported)
# ----------------------------------------------------

# ----------------------------------------------------
# Special commands for RoboDK before post processing
# Use the same commands available with "RDK.Command()"
# Do not use multi-line! RDK_COMMANDS = {} must be a single line!
#
# Example:
#
# RDK_COMMANDS = {
#     "ProgMoveNames": "1",  # Tools->Options->Program->Export target names
#     "ProgMoveExtAxesPoses": "1",  # Tools->Options->Program->Export external axes poses
#     "MoveLSplitMM": "2", # Force-split linear movements into smaller joint movements
#     "MoveCSplitMM": "2",
#     "MoveCSplitDeg": "90",
#     "MoveCSplitMinMM": "0",
#     "ProgMoveJType": "0", # Tools->Options->Programs->Output for joint movements (index = dropbox index, eg. 0 -> Default)
#     "ProgMoveLType": "1", # Tools->Options->Programs->Output for linear movements (index = dropbox index, eg. 1 -> Joint)
#     "ProgMoveCType": "2"  # Tools->Options->Programs->Output for circular movements (index = dropbox index, eg. 2 -> Cartesian)
# }
RDK_COMMANDS = {"ProgMoveNames": "1", "ProgMoveExtAxesPoses": "1"}

# Import RoboDK tools
from robodk import robomath
from robodk import robodialogs
from robodk import robofileio

from robodk.robodialogs import mbox  # For unit tests

from typing import List, Optional, Union


# ----------------------------------------------------
def pose_2_str(pose: robomath.Mat) -> str:
    """Converts a robot pose target to a string according to the syntax/format of the controller.

    **Tip**: Change the output of this function according to your controller.

    :param pose: 4x4 pose matrix
    :type pose: :meth:`robodk.robomath.Mat`
    :return: position as a XYZWPR string
    :rtype: str
    """
    [x, y, z, r, p, w] = robomath.pose_2_xyzrpw(pose)
    return ('X%.3f Y%.3f Z%.3f R%.3f P%.3f W%.3f' % (x, y, z, r, p, w))


def joints_2_str(joints: List[float]) -> str:
    """Converts a robot joint target to a string according to the syntax/format of the controller.

    **Tip**: Change the output of this function according to your controller.

    :param joints: robot joints as a list
    :type joints: float list
    :return: joint format as a J1-Jn string
    :rtype: str
    """
    str = ''
    data = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    for i in range(min(len(joints), len(data))):
        str = str + ('%s%.6f ' % (data[i], joints[i]))
    str = str[:-1]
    return str


def str_2_type(s: Union[str, bool, int, float]) -> Union[str, bool, int, float]:
    """Converts a string containing a numerical or true/false (case insensitive) to a basic data type (bool/int/float).

    :param s: The string to process
    :type s: str
    :return: The basic data type (bool/int/float), or str if it fails
    :rtype: str or bool or int or float
    """
    if type(s) != str:
        return s
    if s.lower() in ['true', 'false']:
        return bool(s)
    try:
        f = float(s)
        if int(f) == f:
            return int(f)
        return f
    except:
        pass
    return s


# ----------------------------------------------------
# Object class that handles the robot instructions/syntax
class RobotPost(object):
    """RoboDK Post Processor object.

    As Post processors can be compiled (.pyc), class variables can be exposed to the user for further customization.

    More information on how users can modify variables of a RoboDK Post Processor here:

        - https://robodk.com/doc/en/Post-Processors.html#PPEditor
        - https://robodk.com/doc/en/Post-Processors.html#EditPost

    .. code-block:: python

        class RobotPost(object):

            # Public: define variables that can be edited by the user below

            MY_PUBLIC_VAR = TRUE

            # ----------------------------------------------------
            # Private: define internal variables that cannot be edited by the user below (note the "# ---------..." splitter)

            MY_PRIVATE_VAR = False

    """

    # Public: define variables that can be edited by the user below
    #
    # More information on how users can modify variables of a RoboDK Post Processor here:
    #     https://robodk.com/doc/en/Post-Processors.html#PPEditor
    #     https://robodk.com/doc/en/Post-Processors.html#EditPost

    # Set the output program extension (for multiple files, handle separately)
    PROG_EXT = 'txt'

    # Default speed for linear moves in mm/s
    DEFAULT_LINEAR_SPEED = 500.0

    # Default acceleration for linear moves in mm/s^2
    DEFAULT_LINEAR_ACCEL = 2000.0

    # Default speed for joint moves in %
    DEFAULT_JOINT_SPEED = 100.0

    # Default acceleration for joint moves in %
    DEFAULT_JOINT_ACCEL = 100.0

    # Default blend radius (corners smoothing) in %
    DEFAULT_BLENDING = 0.0

    # Add the RoboDK frame name as a comment in the output program
    ADD_FRAME_NAME = False

    # Add the RoboDK tool name as a comment in the output program
    ADD_TOOL_NAME = False

    # Add the RoboDK target name as a comment in the output program
    ADD_TARGET_NAME = False

    # Default maximum number of lines per file. If this number is exceeded, the program is splitted in different files.
    # This setting can be overridden in RoboDK (Tools-Options-Program)
    # A value <=0 or None will discard this limit
    DEFAULT_MAX_LINES_X_PROG = None

    # Set to True to create one additional file per subprogram, False to bundle everything in one file
    SAVE_SUBPROGRAMS_SEPARATELY = False

    # ----------------------------------------------------
    # Private: define internal variables that cannot be edited by the user below (note the "# ---------..." splitter)

    # MY_PRIVATE_VAR = False

    # Minimum number of lines required to define at least 1 instruction in an output file
    MIN_LINES_X_PROG = 10

    def __init__(self, robotpost: str = '', robotname: str = '', robot_axes: int = 6, **kwargs) -> None:
        """Create a new post processor.

        **Tip**: Avoid using instances of :meth:`robodk.robolink.Robolink` and/or :meth:`robodk.robolink.Item` in the post processor unless absolutely necessary.

        :param robotpost: Name of the post processor
        :type robotpost: str
        :param robotname: Name of the robot
        :type robotname: str
        :param robot_axes: Number of axes of the robot, including synchronized axes
        :type robot_axes: int
        :param axes_type: Type of each axes of the robot ('R': Robot rotative, 'T': Robot translation, 'J': Ext. axis rotative, 'L': Ext. axis linear)
        :type axes_type: list of str, optional
        :param native_name: Native name of the robot (before any rename)
        :type native_name: str, optional
        :param ip_com: IP address of the robot ("Connect" tab in RoboDK)
        :type ip_com: str, optional
        :param api_port: RoboDK API port to the RoboDK instance
        :type api_port: int, optional
        :param prog_ptr: RoboDK Item pointer to the program generated
        :type prog_ptr: int, optional
        :param robot_ptr: RoboDK Item pointer to the robot associated with the program generated
        :type robot_ptr: int, optional
        :param pose_turntable: Pose of the synchronized turn table
        :type pose_turntable: :meth:`robodk.robomath.PosePP`, optional
        :param pose_rail: Pose of the synchronized linear rail
        :type pose_rail: :meth:`robodk.robomath.PosePP`, optional
        :param lines_x_prog: Maximum number of lines per program (to generate multiple files). This setting can be overridden by in RoboDK (Tools-Options-Program)
        :type lines_x_prog: int, optional
        :param pulses_x_deg: Pulses per degree (provided in the robot parameters of RoboDK)
        :type pulses_x_deg: list of int, optional

        Example for a program using the KUKA KRC2 post processor and a KUKA KR 500 3 robot with synchronized linear rail and turn table:

        .. code-block:: python

            RobotPost(r\"\"\"KUKA_KRC2\"\"\",r\"\"\"KUKA KR 500 3\"\"\",9, axes_type=['R','R','R','R','R','R','T','J','J'], native_name=r\"\"\"KUKA KR 500 3\"\"\", ip_com=r\"\"\"192.168.241.127\"\"\", api_port=20500, prog_ptr=2109546424992, robot_ptr=2109347059584, pose_turntable=p(1890.627070,1670.706012,-504.767930,-0.060103,0.046410,-0.246888), pose_rail=p(0.000000,0.000000,0.000000,90.000000,0.000000,0.000000))

        """

        # Constructor parameters (mandatory)
        self.ROBOT_POST = robotpost  # Name of the robot post processor (provided by RoboDK in the constructor)
        self.ROBOT_NAME = robotname  # Name of the robot (provided by RoboDK in the constructor)
        self.ROBOT_AXES = robot_axes  # Number of axes for the robot, including synchronized axes (provided by RoboDK in the constructor)

        # Optional constructor parameters (added later, backward compatibility)
        self.AXES_TYPE = None  # Optional, type of each axes of the robot ('R': Robot rotative, 'T': Robot translation, 'J': Ext. axis rotative, 'L': Ext. axis linear) (provided by RoboDK in the constructor)
        self.NATIVE_NAME = robotname  # Optional, native/original name of the robot (provided by RoboDK in the constructor)
        self.IP_COM = None  # Optional, IP address of the robot ("Connect" tab in RoboDK) (provided by RoboDK in the constructor)
        self.API_PORT = None  # Optional, RoboDK API port to the RoboDK instance (provided by RoboDK in the constructor)
        self.PROG_PTR = None  # Optional, RoboDK Item pointer to the program generated (provided by RoboDK in the constructor)
        self.ROBOT_PTR = None  # Optional, RoboDK Item pointer to the robot associated with the program generated (provided by RoboDK in the constructor)
        self.POSE_TURNTABLE = None  #  Optional, offset pose of the synchronized turn table (provided by RoboDK in the constructor)
        self.POSE_RAIL = None  # Optional, offset pose of the synchronized linear rail (provided by RoboDK in the constructor)
        self.MAX_LINES_X_PROG = max(self.MIN_LINES_X_PROG, self.DEFAULT_MAX_LINES_X_PROG) if self.DEFAULT_MAX_LINES_X_PROG else None  # Optional, maximum number of lines per program (to generate multiple files). This setting can be overridden in RoboDK (Tools-Options-Program) (provided by RoboDK in the constructor)
        self.PULSES_X_DEG = None  # Optional, pulses per degree (provided in the robot parameters of RoboDK) (provided by RoboDK in the constructor)

        # Optional constructor parameters, you may or may not use those
        for k, v in kwargs.items():
            if k == 'axes_type':
                self.AXES_TYPE = v
            elif k == 'native_name' and v:  # Could be empty for older robots
                self.NATIVE_NAME = v
            elif k == 'ip_com':
                self.IP_COM = v
            elif k == 'api_port':
                self.API_PORT = v
            elif k == 'prog_ptr':
                self.PROG_PTR = v
            elif k == 'robot_ptr':
                self.ROBOT_PTR = v
            elif k == 'pose_turntable':
                self.POSE_TURNTABLE = v
            elif k == 'pose_rail':
                self.POSE_RAIL = v
            elif k == 'lines_x_prog':
                self.MAX_LINES_X_PROG = max(self.MIN_LINES_X_PROG, v)
            elif k == 'pulses_x_deg':
                self.PULSES_X_DEG = v

        self.ROBOT_EXT_AXES = 0  # Number of synchronized external axes for the robot
        if self.AXES_TYPE:
            self.ROBOT_EXT_AXES = self.AXES_TYPE.count('T') + self.AXES_TYPE.count('J')

        # Optional TEMP parameter (depends on RoboDK settings)
        self._TargetName = None  # Optional, target name (Tools->Options->Program->Export target names) (provided by RoboDK in the TEMP file)
        self._TargetNameVia = None  # Optional, intermediary target name (MoveC) (Tools->Options->Program->Export target names) (provided by RoboDK in the TEMP file)
        self._PoseTrack = None  # Optional, current pose of the synchronized linear axis (Tools->Options->Program->Export external axes poses) (provided by RoboDK in the TEMP file)
        self._PoseTurntable = None  # Optional, current pose of the synchronized turn table (Tools->Options->Program->Export external axes poses) (provided by RoboDK in the TEMP file)

        # Initialize internal non-constant variables (caps kept for legacy)
        self.PROG = []  # Current program content (list of str)
        self.PROG_LIST = []  # List of parsed programs (list of parsed "PROG")
        self.PROG_NAMES = []  # List of parsed program names
        self.PROG_FILES = []  # Local files generated by the post processor
        self.PROG_NAME = ''  # Active program name
        self.LOG = ''  # Current log content (str)
        self.ONETAB = '  '  # Tab character(s) (usually white-space or \t)
        self.TAB = ''  # Current tabulation

        # Robot state
        self._frame_name = None  # Current reference frame name, from setFrame
        self._frame_pose = None  # Current reference frame pose, from setFrame
        self._frame_id = 0  # Current reference frame ID, from setFrame

        self._tool_name = None  # Current tool name, from setTool
        self._tool_pose = None  # Current tool pose, from setTool
        self._tool_id = 0  # Current tool ID, from setTool

        self._target_name = None  # Last target name, from MoveL/J/C
        self._target_pose = None  # Last target pose, from MoveL/J/C
        self._target_joints = None  # Last target joints, from MoveL/J/C

        self._speed = self.DEFAULT_LINEAR_SPEED  # Current linear speed, mm/s
        self._acceleration = self.DEFAULT_LINEAR_ACCEL  # Current linear acceleration, mm/s2
        self._speed_joints = self.DEFAULT_JOINT_SPEED  # Current joints speed, %
        self._acceleration_joints = self.DEFAULT_JOINT_ACCEL  # Current joints acceleration, %

        self._blending = self.DEFAULT_BLENDING  # Current blending, %

    def ProgStart(self, progname: str) -> None:
        """Start a new program given a name. Multiple programs can be generated at the same time.

        **Tip**:
        ProgStart is triggered every time a new program must be generated.

        :param progname: Name of the program
        :type progname: str
        """
        self.PROG_NAME = robofileio.FilterName(progname)  # Create a valid program name
        self.PROG_NAMES.append(self.PROG_NAME)  # Keep track of parsed programs

        self.TAB = ''
        if len(self.PROG_NAMES) == 1:
            self.addline('PROC %s()' % self.PROG_NAME)
        else:
            # Sub program
            self.addline('SUB %s()' % self.PROG_NAME)
        self.TAB = self.ONETAB

    def ProgFinish(self, progname: str) -> None:
        """This method is executed to define the end of a program or procedure. One module may have more than one program. No other instructions will be executed before another :meth:`samplepost.RobotPost.ProgStart` is executed.

        **Tip**:
        ProgFinish is triggered after all the instructions of the program.

        :param progname: Name of the program
        :type progname: str
        """
        self.TAB = ''
        if len(self.PROG_NAMES) == 1:
            self.addline('ENDPROC %% %s' % self.PROG_NAME)
        else:
            # Sub program
            self.addline('ENDSUB %% %s' % self.PROG_NAME)
        self.TAB = self.ONETAB

        self.PROG_LIST.append(self.PROG)  # Add the program to the list of parsed programs
        self.PROG = []  # Reset the program buffer for the next program

    def ProgSave(self, folder: str, progname: str, ask_user: bool = False, show_result: Union[bool, str, List[str]] = False) -> None:
        """Saves the program. This method is executed after all programs have been processed.

        **Tip**:
        ProgSave is triggered after all the programs and instructions have been executed.

        :param folder: Folder hint to save the program
        :type folder: str
        :param progname: Program name as a hint to save the program
        :type progname: str
        :param ask_user: True if the default settings in RoboDK are set to prompt the user to select the folder
        :type ask_user: bool, str
        :param show_result: False if the default settings in RoboDK are set to not show the program once it has been saved. Otherwise, a string is provided with the path of the preferred text editor
        :type show_result: bool, str
        """

        # Check if we need to force save subprograms as separate files
        if not self.SAVE_SUBPROGRAMS_SEPARATELY and self.MAX_LINES_X_PROG and len(self.PROG_NAMES) > 0:
            total_lines = sum(len(prog) + 1 for prog in self.PROG_LIST)  # count spaces
            if total_lines > self.MAX_LINES_X_PROG:
                self.addlog("Combined file exceeds the maximum number of lines per file (%d/%d lines). Saving main/subprograms as separate files." % (total_lines, self.MAX_LINES_X_PROG))
                self.SAVE_SUBPROGRAMS_SEPARATELY = True  # Force split per program

        if self.MAX_LINES_X_PROG:
            prog_list = list(self.PROG_LIST)
            prog_names = list(self.PROG_NAMES)
            self.PROG_LIST = []
            self.PROG_NAMES = []

            for prog_name, prog in zip(prog_names, prog_list):
                if self.MAX_LINES_X_PROG and len(prog) > self.MAX_LINES_X_PROG:
                    num_subs = (len(prog) + self.MAX_LINES_X_PROG - 1) // self.MAX_LINES_X_PROG
                    sub_names = []

                    # Main wrapper program that calls the subprograms (reserve main "PROC")
                    self.ProgStart(prog_name)
                    prog = prog[len(self.PROG):]  # Remove header
                    for i in range(num_subs):
                        sub_name = f"{prog_name}_{i+1}"
                        self.RunCode(sub_name, True)
                        sub_names.append(sub_name)
                    size = len(self.PROG)
                    self.ProgFinish(prog_name)
                    footer_size = len(self.PROG_LIST[-1]) - size
                    prog = prog[:-footer_size]  # Remove footer

                    # Generate subprograms
                    for i, sub_name in enumerate(sub_names):
                        self.ProgStart(sub_name)
                        self.PROG += prog[i * self.MAX_LINES_X_PROG:(i + 1) * self.MAX_LINES_X_PROG]
                        self.ProgFinish(sub_name)

                else:
                    self.PROG_NAMES.append(prog_name)
                    self.PROG_LIST.append(prog)

        if (len(self.PROG_NAMES) == 1) or not self.SAVE_SUBPROGRAMS_SEPARATELY:
            # Save to file
            prog_save = self.PROG_NAMES[0] + '.' + self.PROG_EXT
            filesave = folder + '/' + prog_save
            if ask_user or not robofileio.DirExists(folder):
                filesave = robodialogs.getSaveFileName(folder, prog_save)
                if not filesave:
                    return
                folder = filesave.replace('\\', '/').rsplit('/', 1)[0]
        else:
            # Save to folder
            if ask_user or not robofileio.DirExists(folder):
                folder = robodialogs.getSaveFolder(folder)
                if not folder or not robofileio.DirExists(folder):
                    return

        # Here you can create a single file with all programs, or create multiple files for each program
        if (len(self.PROG_NAMES) == 1) or not self.SAVE_SUBPROGRAMS_SEPARATELY:
            filesave = folder + '/' + self.PROG_NAMES[0] + '.' + self.PROG_EXT
            with open(filesave, "w", encoding="utf-8") as fid:
                for prog_name, prog in zip(self.PROG_NAMES, self.PROG_LIST):

                    # Japanese controllers need the "shift_jis" codec and "replace" errors to not throw errors on non supported characters
                    #with open(filesave, "w", encoding="shift_jis", errors="replace") as fid:
                    for line in prog:
                        fid.write(line)
                        fid.write("\n")

                    if prog_name != self.PROG_NAMES[-1]:
                        fid.write("\n")

            print('SAVED: %s\n' % filesave)
            self.PROG_FILES.append(filesave)
        else:
            for prog_name, prog in zip(self.PROG_NAMES, self.PROG_LIST):
                filesave = folder + '/' + prog_name + '.' + self.PROG_EXT

                # Japanese controllers need the "shift_jis" codec and "replace" errors to not throw errors on non supported characters
                #with open(filesave, "w", encoding="shift_jis", errors="replace") as fid:
                with open(filesave, "w", encoding="utf-8") as fid:
                    for line in prog:
                        fid.write(line)
                        fid.write("\n")

                print('SAVED: %s\n' % filesave)
                self.PROG_FILES.append(filesave)

        #----------------------
        # show result
        if show_result:
            if type(show_result) is str:
                # Open file with provided application
                import subprocess
                p = subprocess.Popen([show_result] + self.PROG_FILES[:100])
            elif type(show_result) is list:
                import subprocess
                p = subprocess.Popen(show_result + self.PROG_FILES)
            else:
                # Open file with default application
                import os
                os.startfile(self.PROG_FILES[0])

            if len(self.LOG) > 0:
                mbox('Program generation LOG:\n\n' + self.LOG)

    def ProgSendRobot(self, robot_ip: str, remote_path: str, ftp_user: str, ftp_pass: str) -> None:
        """Send a program to the robot using the provided parameters. This method is executed right after ProgSave if we selected the option "Send Program to Robot".
        The connection parameters must be provided in the robot connection menu of RoboDK.

        :param robot_ip: IP address of the robot
        :type robot_ip: str
        :param remote_path: Remote path of the robot
        :type remote_path: str
        :param ftp_user: FTP user credential
        :type ftp_user: str
        :param ftp_pass: FTP user password
        :type ftp_pass: str
        """
        robofileio.UploadFTP(self.PROG_FILES, robot_ip, remote_path, ftp_user, ftp_pass)

    def MoveJ(self, pose: Optional[robomath.Mat], joints: List[float], conf_RLF: Optional[List[int]]) -> None:
        """Defines a joint movement.

        **Tip**:
        MoveJ is triggered by the RoboDK instruction Program->Move Joint Instruction.

        :param pose: Pose target of the tool with respect to the reference frame. Pose can be None if the target is defined as a joint target
        :type pose: :meth:`robodk.robomath.Mat`, None
        :param joints: Robot joints as a list
        :type joints: float list
        :param conf_RLF: Robot configuration as a list of 3 ints: [REAR, LOWER-ARM, FLIP]. [0,0,0] means [front, upper arm and non-flip] configuration. Configuration can be None if the target is defined as a joint target
        :type conf_RLF: int list, None
        """
        # Some post processor might need to specify the speed, reference frame, active tool, blending, on each motion command
        # Simply store the data as a member variable
        self._target_pose = pose
        self._target_joints = joints

        # Check self._TargetName for a named target
        self._target_name = None
        if self._TargetName is not None and type(self._TargetName) is str:
            self._target_name = robofileio.FilterName(self._TargetName)
            if self.ADD_TARGET_NAME:
                self.RunMessage("Target: " + self._TargetName, True)

        if pose is None:
            # Use absolute joint position
            self.addline('MOVJ ' + joints_2_str(joints))
        else:
            # Check self._PoseTrack and self._PoseTurntable for synchronized external axes poses
            # To enable it, Tools->Options->Program->Export external axes poses
            if self._PoseTrack or self._PoseTurntable:
                if self.POSE_TURNTABLE and self.POSE_RAIL:
                    # Linear track/rail + turn table/positioner
                    pose = robomath.invH(self._PoseTrack * self.POSE_RAIL) * self.POSE_TURNTABLE * self._PoseTurntable * self._frame_pose * pose
                elif self.POSE_TURNTABLE:
                    # Turn table/positioner only
                    pose = self.POSE_TURNTABLE * self._PoseTurntable * self._frame_pose * pose
                elif self.POSE_RAIL:
                    # Linear track/rail
                    pose = robomath.invH(self._PoseTrack * self.POSE_RAIL) * self._frame_pose * pose

            # Optionally, prefer cartesian targets when available
            self.addline('MOVJ ' + pose_2_str(pose))

    def MoveL(self, pose: Optional[robomath.Mat], joints: List[float], conf_RLF: Optional[List[int]]) -> None:
        """Defines a linear movement.

        **Tip**:
        MoveL is triggered by the RoboDK instruction Program->Move Linear Instruction.

        :param pose: Pose target of the tool with respect to the reference frame. Pose can be None if the target is defined as a joint target
        :type pose: :meth:`robodk.robomath.Mat`, None
        :param joints: Robot joints as a list
        :type joints: float list
        :param conf_RLF: Robot configuration as a list of 3 ints: [REAR, LOWER-ARM, FLIP]. [0,0,0] means [front, upper arm and non-flip] configuration. Configuration can be None if the target is defined as a joint target
        :type conf_RLF: int list, None
        """
        # Some post processor might need to specify the speed, reference frame, active tool, blending, on each motion command
        # Simply store the data as a member variable
        self._target_pose = pose
        self._target_joints = joints

        # Check self._TargetName for a named target
        self._target_name = None
        if self._TargetName is not None and type(self._TargetName) is str:
            self._target_name = robofileio.FilterName(self._TargetName)
            if self.ADD_TARGET_NAME:
                self.RunMessage("Target: " + self._TargetName, True)

        # If a MoveL is performed on a joint target, pose will be None
        # If your controller supports linear motion with joint targets, fallback to joints
        if pose is None:
            msg = "Linear movement using joint targets is not supported. Change the target type to cartesian or use a joint movement."
            self.addlog(msg)
            self.RunMessage(msg, True)
            return

        # Check self._PoseTrack and self._PoseTurntable for synchronized external axes poses
        # To enable it, Tools->Options->Program->Export external axes poses
        if self._PoseTrack or self._PoseTurntable:
            if self.POSE_TURNTABLE and self.POSE_RAIL:
                # Linear track/rail + turn table/positioner
                pose = robomath.invH(self._PoseTrack * self.POSE_RAIL) * self.POSE_TURNTABLE * self._PoseTurntable * self._frame_pose * pose
            elif self.POSE_TURNTABLE:
                # Turn table/positioner only
                pose = self.POSE_TURNTABLE * self._PoseTurntable * self._frame_pose * pose
            elif self.POSE_RAIL:
                # Linear track/rail
                pose = robomath.invH(self._PoseTrack * self.POSE_RAIL) * self._frame_pose * pose

        self.addline('MOVL ' + pose_2_str(pose))

    def MoveC(self, pose1: Optional[robomath.Mat], joints1: List[float], pose2: Optional[robomath.Mat], joints2: List[float], conf_RLF_1: Optional[List[int]], conf_RLF_2: Optional[List[int]]) -> None:
        """Defines a circular movement.

        **Tip**:
        MoveC is triggered by the RoboDK instruction Program->Move Circular Instruction.

        :param pose1: Pose target of a point defining an arc (waypoint). Pose can be None if the target is defined as a joint target
        :type pose1: :meth:`robodk.robomath.Mat`, None
        :param pose2: Pose target of the end of the arc (final point). Pose can be None if the target is defined as a joint target
        :type pose2: :meth:`robodk.robomath.Mat`, None
        :param joints1: Robot joints of the waypoint
        :type joints1: float list
        :param joints2: Robot joints of the final point
        :type joints2: float list
        :param conf_RLF_1: Robot configuration of the waypoint as a list of 3 ints: [REAR, LOWER-ARM, FLIP]. [0,0,0] means [front, upper arm and non-flip] configuration. Configuration can be None if the target is defined as a joint target
        :type conf_RLF_1: int list, None
        :param conf_RLF_2: Robot configuration of the final point as a list of 3 ints: [REAR, LOWER-ARM, FLIP]. [0,0,0] means [front, upper arm and non-flip] configuration. Configuration can be None if the target is defined as a joint target
        :type conf_RLF_2: int list, None
        """
        # Some post processor might need to specify the speed, reference frame, active tool, blending, on each motion command
        # Simply store the data as a member variable
        self._target_pose = pose2  # Keep the last target on a MoveC
        self._target_joints = joints2

        # Check self._TargetName and self._TargetNameVia for a named target
        self._target_name = None
        if self._TargetName is not None:
            target1 = ""
            target2 = ""
            if type(self._TargetName) is list and len(self._TargetName) >= 2:
                # RoboDK <5.6.9
                if self._TargetName[0] is not None:
                    target1 = self._TargetName[0]
                if self._TargetName[1] is not None:
                    target2 = self._TargetName[1]
            elif type(self._TargetName) is str:
                # RoboDK >5.6.9
                if self._TargetNameVia is not None:
                    target1 = self._TargetNameVia
                if self._TargetName is not None:
                    target2 = self._TargetName

            self._target_name = robofileio.FilterName(target2)
            if self.ADD_TARGET_NAME:
                self.RunMessage("Target 1: %s" % target1, True)
                self.RunMessage("Target 2: %s" % target2, True)

        # If a MoveC is performed on a joint target, pose will be None
        # If your controller supports linear motion with joint targets, fallback to joints
        if pose1 is None or pose2 is None:
            msg = "Circular movement using joint targets is not supported. Change the target type to cartesian or use a joint movement."
            self.addlog(msg)
            self.RunMessage(msg, True)
            return

        # Check self._PoseTrack and self._PoseTurntable for synchronized external axes poses
        # To enable it, Tools->Options->Program->Export external axes poses
        if self._PoseTrack or self._PoseTurntable:
            if self.POSE_TURNTABLE and self.POSE_RAIL:
                # Linear track/rail + turn table/positioner
                pose1 = robomath.invH(self._PoseTrack * self.POSE_RAIL) * self.POSE_TURNTABLE * self._PoseTurntable * self._frame_pose * pose1
                pose2 = robomath.invH(self._PoseTrack * self.POSE_RAIL) * self.POSE_TURNTABLE * self._PoseTurntable * self._frame_pose * pose2
            elif self.POSE_TURNTABLE:
                # Turn table/positioner only
                pose1 = self.POSE_TURNTABLE * self._PoseTurntable * self._frame_pose * pose1
                pose2 = self.POSE_TURNTABLE * self._PoseTurntable * self._frame_pose * pose2
            elif self.POSE_RAIL:
                # Linear track/rail
                pose1 = robomath.invH(self._PoseTrack * self.POSE_RAIL) * self._frame_pose * pose1
                pose2 = robomath.invH(self._PoseTrack * self.POSE_RAIL) * self._frame_pose * pose2

        self.addline('MOVC ' + pose_2_str(pose1) + ' ' + pose_2_str(pose2))

    def setFrame(self, pose: robomath.Mat, frame_id: int, frame_name: str) -> None:
        """Defines a new reference frame with respect to the robot base frame. This reference frame is used for following pose targets used by movement instructions.

        **Tip**:
        setFrame is triggered by the RoboDK instruction Program->Set Reference Frame Instruction.

        :param pose: Pose of the reference frame with respect to the robot base frame
        :type pose: :meth:`robodk.robomath.Mat`
        :param frame_id: Number of the reference frame (if available, else -1)
        :type frame_id: int
        :param frame_name: Name of the reference frame as defined in RoboDK
        :type frame_name: str
        """
        self._frame_pose = pose
        self._frame_id = frame_id
        self._frame_name = robofileio.FilterName(frame_name)
        if self.ADD_FRAME_NAME and frame_name:
            self.RunMessage("Frame: " + frame_name, True)
        self.addline('BASE_FRAME ' + pose_2_str(pose))

    def setTool(self, pose: robomath.Mat, tool_id: Optional[int], tool_name: str) -> None:
        """Change the robot TCP (Tool Center Point) with respect to the robot flange. Any movement defined in Cartesian coordinates assumes that it is using the last reference frame and tool frame provided.

        **Tip**:
        setTool is triggered by the RoboDK instruction Program->Set Tool Frame Instruction.

        :param pose: Pose of the TCP frame with respect to the robot base frame
        :type pose: :meth:`robodk.robomath.Mat`
        :param tool_id: Tool ID (if available, else -1)
        :type tool_id: int, None
        :param tool_name: Name of the tool as defined in RoboDK
        :type tool_name: str
        """
        self._tool_pose = pose
        self._tool_id = tool_id
        self._tool_name = robofileio.FilterName(tool_name)
        if self.ADD_TOOL_NAME:
            self.RunMessage("Tool: " + tool_name, True)
        self.addline('TOOL_FRAME ' + pose_2_str(pose))

    def Pause(self, time_ms: float) -> None:
        """Defines a pause in a program (including movements). time_ms is negative if the pause must provoke the robot to stop until the user desires to continue the program.

        **Tip**:
        Pause is triggered by the RoboDK instruction Program->Pause Instruction.

        :param time_ms: Time of the pause, in milliseconds
        :type time_ms: float
        """
        if time_ms < 0:
            self.addline('PAUSE')
        else:
            self.addline('WAIT %.3f' % (time_ms * 0.001))

    def setSpeed(self, speed_mms: float) -> None:
        """Changes the robot speed (in mm/s)

        **Tip**:
        setSpeed is triggered by the RoboDK instruction Program->Set Speed Instruction.

        :param speed_mms: Speed in :math:`mm/s`
        :type speed_mms: float
        """
        self._speed = speed_mms
        self.addline('SPEEDL %.2f' % speed_mms)

    def setAcceleration(self, accel_mmss: float) -> None:
        """Changes the robot acceleration (in mm/s^2)

        **Tip**:
        setAcceleration is triggered by the RoboDK instruction Program->Set Speed Instruction. An acceleration value must be provided.

        :param accel_mmss: Speed in :math:`mm/s^2`
        :type accel_mmss: float
        """
        self._acceleration = accel_mmss
        self.addline('ACCELL %.2f' % accel_mmss)

    def setSpeedJoints(self, speed_degs: float) -> None:
        """Changes the robot joint speed (in deg/s)

        **Tip**:
        setSpeedJoints is triggered by the RoboDK instruction Program->Set Speed Instruction. A joint speed value must be provided.

        :param speed_degs: Speed in :math:`deg/s`
        :type speed_degs: float
        """
        self._speed_joints = speed_degs
        self.addline('SPEEDJ %.2f' % speed_degs)

    def setAccelerationJoints(self, accel_degss: float) -> None:
        """Changes the robot joint acceleration (in deg/s^2)

        **Tip**:
        setAccelerationJoints is triggered by the RoboDK instruction Program->Set Speed Instruction. A joint acceleration value must be provided.

        :param accel_degss: Speed in :math:`deg/s^2`
        :type accel_degss: float
        """
        self._acceleration_joints = accel_degss
        self.addline('ACCELJ %.2f' % accel_degss)

    def setZoneData(self, zone_mm: float) -> None:
        """Changes the smoothing radius (also known as rounding, blending radius, CNT, APO or zone data). If this parameter is higher it helps making the movement smoother

        **Tip**:
        setZoneData is triggered by the RoboDK instruction Program->Set Rounding Instruction.

        :param zone_mm: Rounding radius in mm
        :type zone_mm: float
        """
        self._blending = zone_mm
        self.addline('BLEND %.2f' % zone_mm)

    def setDO(self, io_var: Union[int, str], io_value: Union[int, float, str]) -> None:
        """Sets a variable (usually a digital output) to a given value. This method can also be used to set other variables.

        **Tip**:
        setDO is triggered by the RoboDK instruction Program->Set or Wait I/O Instruction.

        :param io_var: Variable to set, provided as a str or int
        :type io_var: int, str
        :param io_value: Value of the variable, provided as a str, float or int
        :type io_value: int, float, str
        """
        if type(io_var) != str:
            io_var = 'DO[%s]' % str(io_var)

        io_value = str_2_type(io_value)
        if type(io_value) != str:
            if io_value > 0:
                io_value = 'TRUE'
            else:
                io_value = 'FALSE'

        self.addline('%s=%s' % (io_var, io_value))

    def setAO(self, io_var: Union[int, str], io_value: Union[int, float, str]) -> None:
        """Sets a an analog variable to a given value.

        **Tip**:
        setAO is triggered by the RoboDK instruction Program->Set or Wait I/O Instruction.

        :param io_var: Variable to set, provided as a str or int
        :type io_var: int, str
        :param io_value: Value of the variable, provided as a str, float or int
        :type io_value: int, float, str
        """
        if type(io_var) != str:
            io_var = 'AO[%s]' % str(io_var)

        io_value = str_2_type(io_value)
        if type(io_value) != str:
            io_value = '%.3f' % float(io_value)

        self.addline('%s=%s' % (io_var, io_value))

    def waitDI(self, io_var: Union[int, str], io_value: Union[int, float, str], timeout_ms: float = -1) -> None:
        """Waits for a variable (usually a digital input) to attain a given value io_value. This method can also be used to set other variables.Optionally, a timeout can be provided.

        **Tip**:
        waitDI is triggered by the RoboDK instruction Program->Set or Wait I/O Instruction.

        :param io_var: Variable to wait for, provided as a str or int
        :type io_var: int, str
        :param io_value: Value of the variable, provided as a str, float or int
        :type io_value: int, float, str
        :param timeout_ms: Maximum wait time
        :type timeout_ms: float, int
        """
        if type(io_var) != str:
            io_var = 'DI[%s]' % str(io_var)

        io_value = str_2_type(io_value)
        if type(io_value) != str:
            if io_value > 0:
                io_value = 'TRUE'
            else:
                io_value = 'FALSE'

        if timeout_ms < 0:
            self.addline('WAIT FOR %s==%s' % (io_var, io_value))
        else:
            self.addline('WAIT FOR %s==%s TIMEOUT=%.1f' % (io_var, io_value, timeout_ms))

    def RunCode(self, code: str, is_function_call: bool = False) -> None:
        """Adds code or a function call.

        **Tip**:
        RunCode is triggered by the RoboDK instruction Program->Function call Instruction.

        :param code: Code or procedure to call. If is_function_call is True, code may already
            include call arguments, e.g. "MyProg(1,2)"
        :param is_function_call: True if the provided code is a specific function to call
        :type code: str
        :type is_function_call: bool
        """
        if is_function_call:
            # Filter only the name: filtering the whole string would strip the comma/space
            # out of any existing call arguments, e.g. "Prog(1, 2)" -> "Prog(12)"
            name, args = code, '()'
            if '(' in code:
                name, args = code.split('(', 1)
                args = '(' + args
            code = robofileio.FilterName(name.strip()) + args
            self.addline(code)
        else:
            self.addline(code)

    def RunMessage(self, message: str, iscomment: bool = False) -> None:
        """Display a message in the robot controller screen (teach pendant)

        **Tip**:
        RunMessage is triggered by the RoboDK instruction Program->Show Message Instruction.

        :param message: Message to display on the teach pendant or as a comment on the code
        :type message: str
        :param iscomment: True if the message does not have to be displayed on the teach pendant but as a comment on the code
        :type iscomment: bool
        """
        if iscomment:
            self.addline('% ' + message)
        else:
            self.addline('TP "%s"' % message)

    # ------------------ private ----------------------

    def addline(self, newline: str) -> None:
        """Add a new program line. This is a private method used only by the other methods.

        :param newline: New program line to add
        :type newline: str
        """
        self.PROG.append(self.TAB + newline)

    def addlog(self, newline: str) -> None:
        """Add a message to the log. This is a private method used only by the other methods. The log is displayed when the program is generated to show any issues when the robot program has been generated.

        :param newline: New log line to add
        :type newline: str
        """
        self.LOG = self.LOG + newline + '\n'


# -------------------------------------------------
# ------------ For testing purposes ---------------
def test_post() -> None:
    """Test the post processor with a simple program"""

    from robodk.robomath import PosePP as p

    r = RobotPost(r"""SamplePost""", r"""RoboDK Industrial""", 6, axes_type=['R', 'R', 'R', 'R', 'R', 'R'])
    r.ProgStart(r"""SampleProgram""")
    r.RunMessage(r"""Set reference""",True)
    r.setFrame(p(640.289,-290,0,90,0,0),1,r"""Part 1""")
    r.RunMessage(r"""Set tool (TCP)""",True)
    r.setTool(p(116.058,0,219.481,0,60,0),-1,r"""Spindle""")
    r.RunMessage(r"""Joint movement""",True)
    r.MoveJ(p(25,125,235,90,0,-180),[40.1663,-71.3949,131.333,60.0149,-40.159,-30.0666],[0,0,1])
    r.RunMessage(r"""Show message to user example""")
    r.RunMessage(r"""Set the speed to 100 mm/s""",True)
    r.setSpeed(100.000)
    r.RunMessage(r"""Set the digital output 5 (DO5) to be 1/On/True""",True)
    r.setDO('DO5',1)
    r.RunMessage(r"""Pause for 2 seconds""",True)
    r.Pause(2000.0)
    r.RunMessage(r"""Wait for digital input (DI2 to be 1/On)""",True)
    r.waitDI('DI2',1,-1)
    r.RunMessage(r"""Joint movement""",True)
    r.MoveL(p(25,25,35,90,0,-180),[9.43828,-44.9426,125.087,9.57705,-80.2793,-1.63183],[0,0,1])
    r.RunMessage(r"""Call a subprogram""",True)
    r.RunCode(r"""SubProg1""", True)
    r.RunMessage(r"""Set rounding/blending to 2 mm""",True)
    r.setZoneData(2.000)
    r.RunMessage(r"""Two linear movements""",True)
    r.MoveL(p(25,25,5,90,0,-180),[9.43828,-40.7002,124.04,9.50125,-83.4302,-1.09702],[0,0,1])
    r.MoveL(p(125,25,5,90,0,-180),[-57.3793,-35.8383,153.204,-126.861,-32.6519,-27.3405],[0,0,1])
    r.RunMessage(r"""One circular movement""",True)
    r.MoveC(p(225,25,35,90,0,-180),[-40.9582,-45.8498,146.604,-123.74,-46.6544,-11.1732],p(225,125,35,90,0,-180),[-52.695,-46.0658,136.671,-142.417,-52.7231,-0.461288],[0,0,1],[0,0,1])
    r.ProgFinish(r"""SampleProgram""")
    # r.ProgSave(r""".""",r"""MAIN_1""",False,False)

    for prog in r.PROG_LIST:
        for line in prog:
            print(line)
        print('')

    if len(r.LOG) > 0:
        mbox('Program generation LOG:\n\n' + r.LOG)


if __name__ == "__main__":
    """Procedure to call when the module is executed by itself: test_post()"""
    test_post()
