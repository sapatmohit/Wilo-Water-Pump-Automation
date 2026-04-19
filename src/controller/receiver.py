import time
import sys
from sx127x import SX127x

# Configuration
# Assuming standard RPi wiring:
# NSS/CS  -> GPIO8 (CE0) (SPI Bus 0, Device 0)
# RESET   -> GPIO25
# DIO0    -> GPIO24

# For wiring verification: https://pinout.xyz/

try:
    print("Initializing LoRa Receiver...")
    lora = SX127x(spi_bus=0, spi_cs=0, reset_pin=25, dio0_pin=24, frequency=433E6)
    
    print("LoRa Initialized. Listening for packets...")
    lora.receive()

    while True:
        if lora.available():
            try:
                payload_data = lora.read_payload()
                # Convert bytes to string (ignoring errors for robustness)
                payload_str = "".join([chr(c) for c in payload_data])
                
                rssi = lora.get_packet_rssi()
                snr = lora.get_packet_snr()

                print(f"Received Packet: '{payload_str}' | RSSI: {rssi} dBm | SNR: {snr:.2f} dB")
            except Exception as e:
                print(f"Error parsing packet: {e}")

        # Reduce CPU load
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopping...")
except Exception as e:
    print(f"\nError: {e}")
finally:
    try:
        lora.close()
    except:
        pass
