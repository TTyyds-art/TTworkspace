class ConduitBean:

    def __init__(self):
        self.conduit = ''
        self.conduit_type = ''
        self.name = ''
        self.speed = ''
        self.allowance = ''
        self.level = ''

    # Get and Set methods
    def get_conduit(self):
        return self.conduit

    def set_conduit(self, conduit):
        self.conduit = conduit

    def get_conduit_type(self):
        return self.conduit_type

    def set_conduit_type(self, conduit_type):
        self.conduit_type = conduit_type

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_speed(self):
        return self.speed

    def set_speed(self, speed):
        self.speed = speed

    def get_allowance(self):
        return self.allowance

    def set_allowance(self, allowance):
        self.allowance = allowance

    def get_level(self):
        return self.level

    def set_level(self, level):
        self.level = level

    # toString method
    def __str__(self):
        return (f"ConduitBean(conduit='{self.conduit}', conduit_type='{self.conduit_type}', "
                f"name='{self.name}', speed='{self.speed}', allowance='{self.allowance}', level='{self.level}')")
