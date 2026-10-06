from robodk import robolink  # RoboDK API

RDK = robolink.Robolink()

# NOTE: use appropriate robot and axis names
robot = RDK.Item('', itemtype=robolink.ITEM_TYPE_ROBOT)

axis_1 = RDK.Item('Turntable3 1 Flange1')
axis_2 = RDK.Item('Turntable3 1 Flange2')

robot.setLink(axis_1)
RDK.setParam('side', 1)
