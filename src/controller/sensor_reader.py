"""
Current & Voltage Sensor Reader (ADS1115 + SCT013 + ZMPT101B)
===============================================================
Reads analog sensors via ADS1115 I2C ADC on the Raspberry Pi.
"""

import time
import math
import logging
from typing import Optional

logger = logging.getLogger('wilo.sensors')

_ADS_OK = False
try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    _ADS_OK = True
except ImportError:
    pass

class SensorReader:
    def __init__(self, acs_model='30A', acs_zero_v=2.5,
                 acs_divider=1.0, zmpt_cal=1.0,
                 zmpt_zero_v=2.5, zmpt_divider=1.0,
                 adc_addr=0x48, ch_current=0, ch_voltage=1):
        
        # Hardcoded CT Sensor Config (100A/50mA with 22 ohm burden resistor)
        self.ct_cal      = 90.91
        
        # Hardcoded Voltage Sensor Config
        self.zmpt_cal    = 916.43
        self.zmpt_zero   = 2.5
        self.zmpt_div    = 1.0
        
        self.adc_addr    = adc_addr
        
        # Hardware channels on ADS1115
        self.ch_i_pos    = 0
        self.ch_i_neg    = 3
        self.ch_v        = 1

        self.ads         = None
        self.chan_i       = None
        self.chan_v       = None
        self.zmpt_midpoint = 2.5
        self.available   = False

    def initialize(self) -> bool:
        if not _ADS_OK:
            logger.warning("ADS1115 library not installed -> sensor reading disabled.")
            return False
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.ads = ADS.ADS1115(i2c, address=self.adc_addr)
            self.ads.gain = 2/3
            
            # Differential read for Current (A0-A3)
            self.chan_i = AnalogIn(self.ads, self.ch_i_pos, self.ch_i_neg)
            
            # Single-Ended read for Voltage (A1)
            self.chan_v = AnalogIn(self.ads, self.ch_v)
            
            logger.info("Waiting 3 seconds to ensure pump is completely off before calibration...")
            time.sleep(3)
            logger.info("Calibrating True Zero-Point for Voltage sensor...")
            
            # Calibrate Voltage Sensor
            raw_v_list = []
            for _ in range(250):
                raw_v_list.append(self.chan_v.voltage / self.zmpt_div)
                time.sleep(0.002)
            self.zmpt_midpoint = sum(raw_v_list) / len(raw_v_list)
            
            self.available = True
            logger.info(f"ADS1115 OK  current->Diff(A{self.ch_i_pos}-A{self.ch_i_neg})  voltage->A{self.ch_v} ({self.zmpt_midpoint:.3f}V zero)")
            return True
        except Exception as e:
            logger.error(f"ADS1115 init failed: {e}")
            return False

    def read_current_rms(self, samples: int = 60) -> Optional[float]:
        if not self.available:
            return None
        try:
            raw_v = []
            for _ in range(samples):
                raw_v.append(self.chan_i.voltage)
                time.sleep(0.002)
            
            sq_sum = 0.0
            for v_sensor in raw_v:
                # Differential mode automatically centers around 0V!
                i_inst = v_sensor * self.ct_cal
                sq_sum += i_inst * i_inst
                
            rms_amps = math.sqrt(sq_sum / samples)
            
            # Noise floor filter
            if rms_amps < 0.30:
                rms_amps = 0.0
                
            return round(rms_amps, 2)
        except Exception as e:
            logger.error(f"Current read error: {e}")
            return None

    def read_voltage_rms(self, samples: int = 60) -> Optional[float]:
        if not self.available:
            return None
        try:
            raw_v = []
            for _ in range(samples):
                raw_v.append(self.chan_v.voltage / self.zmpt_div)
                time.sleep(0.002)
            
            dc_offset = self.zmpt_midpoint
            sq_sum = 0.0
            for v_sensor in raw_v:
                v_inst = (v_sensor - dc_offset) * self.zmpt_cal
                sq_sum += v_inst * v_inst
                
            return round(math.sqrt(sq_sum / samples), 1)
        except Exception as e:
            logger.error(f"Voltage read error: {e}")
            return None

    def read_all(self) -> dict:
        return {
            'current_amps': self.read_current_rms(),
            'voltage_ac':   self.read_voltage_rms(),
            'available':    self.available,
        }
