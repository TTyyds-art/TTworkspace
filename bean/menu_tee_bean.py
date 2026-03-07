class MenuTeeBean:
    def __init__(self):
        self.ID = ''
        self.Name = ''
        self.Type = ''
        self.Base_Price = ''
        self.Sweetness_Options = ''
        self.Temperature_Options = ''
        self.Size_Options = ''
        self.Add_ons = ''
        self.Image_path = ''
        self.Recipe = ''

    # Getter and Setter for ID
    def get_Image_path(self):
        return self.Image_path

    def set_Image_path(self, Image_path):
        self.Image_path = Image_path

    # Getter and Setter for ID
    def get_ID(self):
        return self.ID

    def set_ID(self, ID):
        self.ID = ID

    # Getter and Setter for Name
    def get_Name(self):
        return self.Name

    def set_Name(self, Name):
        self.Name = Name

    # Getter and Setter for Type
    def get_Type(self):
        return self.Type

    def set_Type(self, Type):
        self.Type = Type

    # Getter and Setter for Base_Price
    def get_Base_Price(self):
        return self.Base_Price

    def set_Base_Price(self, Base_Price):
        self.Base_Price = Base_Price

    # Getter and Setter for Sweetness_Options
    def get_Sweetness_Options(self):
        return self.Sweetness_Options

    def set_Sweetness_Options(self, Sweetness_Options):
        self.Sweetness_Options = Sweetness_Options

    # Getter and Setter for Temperature_Options
    def get_Temperature_Options(self):
        return self.Temperature_Options

    def set_Temperature_Options(self, Temperature_Options):
        self.Temperature_Options = Temperature_Options

    # Getter and Setter for Size_Options
    def get_Size_Options(self):
        return self.Size_Options

    def set_Size_Options(self, Size_Options):
        self.Size_Options = Size_Options

    # Getter and Setter for Add_ons
    def get_Add_ons(self):
        return self.Add_ons

    def set_Add_ons(self, Add_ons):
        self.Add_ons = Add_ons
    
    def set_Tips(self, tips):
        self.tips = tips

    def get_Tips(self):
        return getattr(self, "tips", "")

    # toString method
    def toString(self):
        return (f"MenuTeeBean[ID={self.ID}, Name={self.Name}, Type={self.Type}, "
                f"Base_Price={self.Base_Price}, Sweetness_Options={self.Sweetness_Options}, "
                f"Temperature_Options={self.Temperature_Options}, Size_Options={self.Size_Options}, "
                f"Add_ons={self.Add_ons}]")
