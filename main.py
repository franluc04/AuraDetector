# main.py

# HW Drivers Library --- #
import machine
# --- Async Tasks Management Library --- #
import uasyncio as asyncio
# --- Bluetooth Management Libraries --- #
import bluetooth
import aioble 

# --- Arduino Serial Configuration (UART)---
# GPIO 16 (RX) e GPIO 17 (TX), Baudrate 9600.
uart = machine.UART(2, baudrate=9600, tx=17, rx=16)

# --- BLE Service Definition (Standard Nordic UART Service) --- #
_UART_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_RX_CHAR_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX_CHAR_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

# --- Instantiate BLE Service Via aioble --- #
uart_service = aioble.Service(_UART_SERVICE_UUID)
# --- RX Characteristic: Data Received From The Client (Write) --- #
rx_characteristic = aioble.Characteristic(uart_service, _UART_RX_CHAR_UUID, write=True)
# --- TX Characteristic: Data Sent To The Client (Notify) --- #
tx_characteristic = aioble.Characteristic(uart_service, _UART_TX_CHAR_UUID, notify=True)
# --- Service Registration To BLE Stack
aioble.register_services(uart_service)

print("#" * 40)
print("[ESP32] Ready!")
print("#" * 40)

# --- Global Set For Tracking Active Connections --- #
connections = set()

async def uart_rx_task():
    """
    Async Task To Read Data From Arduino And Transmit Via BLE With BUffering
    """
    
    buffer = b'' 
    while True:
        if uart.any():
            data = uart.read() # Read Blocks Of Available Data
            if data:
                buffer += data
                
                # --- Buffering And Splitting System Based On Newline --- #
                if b'\n' in buffer:
                    lines = buffer.split(b'\n')
                    
                    # --- Process All Complete Lines Besides The Last One (incomplete) --- #
                    for i in range(len(lines) - 1):
                        complete_line_bytes = lines[i] + b'\n'
                        
                        data_string = complete_line_bytes.decode('utf-8', 'ignore').strip()
                        
                       # --- Print Processed Lines --- #
                        if data_string:
                            print(f"{data_string}")

                            # --- Broadcast Data To All Connected Clients --- #
                            if connections:
                                for conn in connections:
                                    try:
                                        tx_characteristic.notify(conn, complete_line_bytes)
                                    except Exception:
                                        print("#" * 40)
                                        print("[ESP32] Connection Lost!")
                                        print("#" * 40)
                                        machine.reset()

                    # --- Keep In The Buffer The Last Incomplete Fragment --- #
                    buffer = lines[-1]

        await asyncio.sleep_ms(20) # Yields xecution To Allow Other Tasks To Run


# --- BLE_MAIN_TASK --- #

async def ble_main_task():
    """
    Main async task to handle BLE connections and advertising
    """
    global connections
    
    while True:
        print("#" * 40)
        print("[ESP32] Advertising Started. Waiting For Connection...")
        print("#" * 40)
        try:
            # --- Wait For The Connection With advertise() Method
            conn = await aioble.advertise(
                250000, 
                name="ESP32_auradetector", 
                services=[_UART_SERVICE_UUID]
            )
            
            print("#" * 40)
            print("[ESP32] Client Connected!")
            print("#" * 40)
            connections.add(conn)
            
            # --- Remaining In This Loop While Connected --- #
      
            # --- Wait For Client Disconnection Before Restarting --- #
            await conn.disconnected()
            print("#" * 40)
            print("[ESP32] Client Disconnected!")
            print("#" * 40)
            
            # --- Connections Set Cleaning And Sys Reset --- #
            connections.clear()
            await asyncio.sleep_ms(500)
            machine.reset()
        
        # --- Errors Management --- #
        except Exception as e:
            print("#" * 40)
            print(f"BLE Error: {e}")
            print("#" * 40)
            machine.reset()
            
# --- START MAIN ASYNC LOOP --- #
loop = asyncio.get_event_loop()
loop.create_task(uart_rx_task())
loop.create_task(ble_main_task())
loop.run_forever()

