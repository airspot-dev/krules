
from krules_core.base_functions import *
from geopy import distance
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="KRules", timeout=10)


class SetLocationProperties(RuleFunctionBase):

    def execute(self):

        coords = (float(self.payload["data"]["lat"]), float(self.payload["data"]["lng"]))
        self.subject.coords = str(coords)
        # ensure ref point is already set
        if "refCoords" not in self.subject:
            self.subject.m_refCoords = str(coords)
        # set location if not already set or if tolerance is exceeded
        if "location" not in self.subject or distance.distance(
                self.subject.m_refCoords, coords
            ).meters > float(self.subject.tolerance):
            self.subject.location = geolocator.reverse("{}, {}".format(coords[0], coords[1])).address
            self.subject.m_refCoords = coords