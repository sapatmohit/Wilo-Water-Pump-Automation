
import spidev
import RPi.GPIO as GPIO
import time

# Register Constants (SX127x)
REG_FIFO                    = 0x00
REG_OP_MODE                 = 0x01
REG_FRF_MSB                 = 0x06
REG_FRF_MID                 = 0x07
REG_FRF_LSB                 = 0x08
REG_PA_CONFIG               = 0x09
REG_LNA                     = 0x0C
REG_FIFO_ADDR_PTR           = 0x0D
REG_FIFO_TX_BASE_ADDR       = 0x0E
REG_FIFO_RX_BASE_ADDR       = 0x0F
REG_FIFO_RX_CURRENT_ADDR    = 0x10
REG_IRQ_FLAGS               = 0x12
REG_RX_NB_BYTES             = 0x13
REG_PKT_SNR_VALUE           = 0x19
REG_PKT_RSSI_VALUE          = 0x1A
REG_MODEM_CONFIG_1          = 0x1D
REG_MODEM_CONFIG_2          = 0x1E
REG_PREAMBLE_MSB            = 0x20
REG_PREAMBLE_LSB            = 0x21
REG_PAYLOAD_LENGTH          = 0x22
REG_MODEM_CONFIG_3          = 0x26
REG_RSSI_WIDEBAND           = 0x2C
REG_DETECTION_OPTIMIZE      = 0x31
REG_INVERT_IQ               = 0x33
REG_DETECTION_THRESHOLD     = 0x37
REG_SYNC_WORD               = 0x39
REG_DIO_MAPPING_1           = 0x40
REG_VERSION                 = 0x42

# Modes
MODE_LONG_RANGE_MODE        = 0x80
MODE_SLEEP                  = 0x00
MODE_STDBY                  = 0x01
MODE_TX                     = 0x03
MODE_RX_CONTINUOUS          = 0x05
MODE_RX_SINGLE              = 0x06

# PA Config
PA_BOOST                    = 0x80

# IRQ Flags
IRQ_TX_DONE_MASK            = 0x08
IRQ_PAYLOAD_CRC_ERROR_MASK  = 0x20
IRQ_RX_DONE_MASK            = 0x40

class SX127x:
    def __init__(self, spi_bus=0, spi_cs=0, reset_pin=25, dio0_pin=24, frequency=433E6):
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_cs)
        self.spi.max_speed_hz = 5000000
        
        self.reset_pin = reset_pin
        self.dio0_pin = dio0_pin
        self.frequency = frequency
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.reset_pin, GPIO.OUT)
        GPIO.setup(self.dio0_pin, GPIO.IN)

        self.reset()
        self.init()

    def reset(self):
        GPIO.output(self.reset_pin, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(self.reset_pin, GPIO.HIGH)
        time.sleep(0.01)

    def write_register(self, addr, value):
        self.spi.xfer2([addr | 0x80, value])

    def read_register(self, addr):
        resp = self.spi.xfer2([addr & 0x7F, 0x00])
        return resp[1]

    def init(self):
        # Check version
        version = self.read_register(REG_VERSION)
        if version != 0x12:
            print(f"Warning: Unknown LoRa chip version: 0x{version:02X}")
        else:
            print(f"SX127x Version: 0x{version:02X}")

        self.sleep()
        self.write_register(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_SLEEP)
        self.standby()
        
        self.set_frequency(self.frequency)
        
        # Match the Arduino LoRa library defaults used by the ESP32 sender:
        # SF7, BW 125 kHz, CR 4/5, explicit header, CRC off.
        self.write_register(REG_FIFO_TX_BASE_ADDR, 0x00)
        self.write_register(REG_FIFO_RX_BASE_ADDR, 0x00)
        self.write_register(REG_LNA, self.read_register(REG_LNA) | 0x03)
        self.write_register(REG_MODEM_CONFIG_3, 0x04)
        
        # Config 1: Bw=125kHz (0x70), CR=4/5 (0x02) -> 0x72
        self.write_register(REG_MODEM_CONFIG_1, 0x72)
        
        # Config 2: SF=7, CRC disabled to match the Arduino LoRa sender.
        self.write_register(REG_MODEM_CONFIG_2, 0x70)
        
        # Preamble length 8
        self.write_register(REG_PREAMBLE_MSB, 0x00)
        self.write_register(REG_PREAMBLE_LSB, 0x08)

        # Sync Word
        self.write_register(REG_SYNC_WORD, 0xF3)

        # PA Boost (kept for parity with the Arduino sender setup)
        self.write_register(REG_PA_CONFIG, PA_BOOST | 0xF)

    def set_frequency(self, freq):
        self.frequency = freq
        frf = int((freq * 524288) / 32000000)
        self.write_register(REG_FRF_MSB, (frf >> 16) & 0xFF)
        self.write_register(REG_FRF_MID, (frf >> 8) & 0xFF)
        self.write_register(REG_FRF_LSB, frf & 0xFF)

    def sleep(self):
        self.write_register(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_SLEEP)

    def standby(self):
        self.write_register(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STDBY)

    def receive(self):
        self.write_register(REG_FIFO_ADDR_PTR, 0x00)
        self.write_register(REG_DIO_MAPPING_1, 0x00) # DIO0 -> RxDone
        self.write_register(REG_IRQ_FLAGS, 0xFF)
        self.write_register(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_RX_CONTINUOUS)

    def available(self):
        # Check IRQ flags
        irq_flags = self.read_register(REG_IRQ_FLAGS)
        if (irq_flags & IRQ_RX_DONE_MASK):
            # Clear IRQ
            self.write_register(REG_IRQ_FLAGS, IRQ_RX_DONE_MASK)
            return True
        return False
    
    def get_packet_rssi(self):
        rssi = self.read_register(REG_PKT_RSSI_VALUE)
        return rssi - 164 # 433 MHz low-band offset for SX1278

    def get_packet_snr(self):
        raw_snr = self.read_register(REG_PKT_SNR_VALUE)
        if raw_snr > 127:
            raw_snr -= 256
        return raw_snr * 0.25

    def read_payload(self):
        # Read payload length
        # In explicit header mode (default), reading REG_RX_NB_BYTES is correct
        length = self.read_register(REG_RX_NB_BYTES)
        
        # Set FIFO ptr to start of RX
        current_addr = self.read_register(REG_FIFO_RX_CURRENT_ADDR)
        self.write_register(REG_FIFO_ADDR_PTR, current_addr)
        
        payload = []
        for i in range(length):
            payload.append(self.read_register(REG_FIFO))
            
        return payload

    def close(self):
        self.spi.close()
        GPIO.cleanup()
