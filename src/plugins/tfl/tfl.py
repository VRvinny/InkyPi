from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
import os
import requests
import logging
from datetime import datetime, timezone
import pytz
from io import BytesIO

logger = logging.getLogger(__name__)


# Must be one of the following: Jubilee, Victoria, Central, Circle, District, DLR, Elizabeth, Hammersmith-City, Northern, Piccadilly, Waterloo-City
CHOSEN_LINE="jubilee"
CHOSEN_STATION="Canary Wharf"

class Tfl(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['style_settings'] = True

        return template_params

    def generate_image(self, settings, device_config):
        template_params = self.get_tfl_data()
        template_params["plugin_settings"] = settings

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]        

        try:
            image = self.render_image(dimensions, "tfl.html", "tfl.css", template_params)
        except Exception as e:
            logger.critical(f"Unable to render screenshot: {str(e)}")
            raise RuntimeError("Failed to take screenshot, please check logs.")

        return image

    def get_tfl_data(self):
        data = {}

        # fetch the status and arrivals data from the APIs
        data['statuses'] = self.get_tfl_line_statuses()
        arrivals = self.get_tfl_next_trains()
        

        data['arrivalW'] = arrivals[0]
        data['arrivalE'] = arrivals[1]
        
        return data

    
    def get_tfl_line_statuses(self):
        hdr ={
            'Cache-Control': 'no-cache',
        }
        statuses = []
        
        try:
            r = requests.get("https://api.tfl.gov.uk/Line/Jubilee,Victoria,Central,Circle,District,DLR,Elizabeth,hammersmith-city,northern,piccadilly/Status", headers=hdr)
            response = r.json()
        except:
            raise RuntimeError("Unable to make statuses request")
            return []


        for i in range(len(response)):
            if response[i]["name"] == "Hammersmith & City":
                response[i]["name"] = "Hammersmith"
            statuses.append([response[i]["name"], "", response[i]["lineStatuses"][0]['statusSeverityDescription'], response[i]["lineStatuses"][0]['statusSeverity']])
        return statuses
    
    def get_tfl_next_trains(self):
        hdr ={
        'Cache-Control': 'no-cache',
        }
        try:
            res = requests.get(f"https://api.tfl.gov.uk/Line/{CHOSEN_LINE}/Arrivals", headers=hdr)
            jsonres = res.json()
        except:
            raise RuntimeError("Unable to make arrivals request")

        #arbitrary directions since stations can be {north,south,west,east}bound
        redbound = []
        bluebound = []

        for i in range(len(jsonres)):
            if CHOSEN_STATION in jsonres[i]["stationName"]:    
                ## inbound/outbound doesnt work with circle line
                if "inbound" in jsonres[i]["direction"]:
                    redbound.append([     jsonres[i]["towards"], jsonres[i]["currentLocation"], jsonres[i]["platformName"], jsonres[i]["timeToStation"], jsonres[i]["timeToStation"]//60    ])
                elif "outbound" in jsonres[i]["direction"] :
                    bluebound.append([     jsonres[i]["towards"], jsonres[i]["currentLocation"], jsonres[i]["platformName"], jsonres[i]["timeToStation"], jsonres[i]["timeToStation"]//60    ])
                else:
                    print("ERROR")

        redbound = sorted(redbound, key=lambda x: x[3])
        bluebound = sorted(bluebound, key=lambda x: x[3])
        # return the top 5 results
        return [redbound[:5], bluebound[:5]]
