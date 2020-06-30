from emonhub_interfacer import EmonHubInterfacer
from collections import defaultdict
import time
import atexit

import Cargo

try:
    import RPi.GPIO as GPIO
    RPi_found = True
except:
    RPi_found = False

"""class EmonhubPulseCounterInterfacer

Authors @borpin & @bwduncan
Version: 1
Date: 11 June 2020

Monitors GPIO pins for pulses

Example emonhub configuration
[[pulse2]]
    Type = EmonHubPulseCounterInterfacer
    [[[init_settings]]]
        # pin number must be specified. Create a second
        # interfacer for more than one pulse sensor
        pulse_pin = 15
        # bouncetime default to 1.
        # bouncetime = 2
    [[[runtimesettings]]]
        pubchannels = ToEmonCMS,

        # Default NodeID is 0. Use nodeoffset to set NodeID
        # No decoder required as key:value pair returned
        nodeoffset = 3
"""

class EmonHubPulseCounterInterfacer(EmonHubInterfacer):

    def __init__(self, name, pulse_pin=None, bouncetime=1):
        """Initialize interfacer

        """

        # Initialization
        super().__init__(name)

        self._settings.update( {
            'pulse_pin': int(pulse_pin),
            'bouncetime' : bouncetime,
        })

        self._pulse_settings = {}

        self.pulse_count = 0

        self.last_pulse = 0

        self.last_time = (time.time()//10)*10

        if RPi_found:
            self.init_gpio()
        else:
            self._log.error("Pulse counter not initialised. Please install the RPi GPIO Python3 module")

    def init_gpio(self):
        """Register GPIO callbacks

        """

        atexit.register(GPIO.cleanup)
        GPIO.setmode(GPIO.BOARD)
        self._log.info('%s : Pulse pin set to: %d', self.name, self._settings['pulse_pin'])
        GPIO.setup(self._settings['pulse_pin'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(self._settings['pulse_pin'], GPIO.FALLING, callback=self.process_pulse, bouncetime=int(self._settings['bouncetime']))

    def process_pulse(self, channel):
        self.pulse_count += 1
        self._log.debug('%s : pulse received -  count: %d', self.name, self.pulse_count)

    def read(self):

        time_now = time.time()

        if self.last_pulse == self.pulse_count:
            return False
        elif self.last_time + 2 > time_now:
            return False

        self._log.debug('Data to Post: last_time: %d  time_now: %d', self.last_time, time_now)
        self.last_pulse = self.pulse_count
        self.last_time = int(time_now)

        c = Cargo.new_cargo(nodename=self.name, timestamp=time_now)
        c.names = ["Pulse"]
        c.realdata = [self.last_pulse]

        if int(self._settings['nodeoffset']):
            c.nodeid = int(self._settings['nodeoffset'])
        else:
            c.nodeid = 0
        return c


    def set(self, **kwargs):
        super().set(**kwargs)

        for key, setting in self._pulse_settings.items():

            if key not in kwargs:
                setting = self._pulse_settings[key]
            else:
                setting = kwargs[key]

            if key in self._settings and self._settings[key] == setting:
                continue
            else:
                self._log.warning("'%s' is not valid for %s: %s", setting, self.name, key)
