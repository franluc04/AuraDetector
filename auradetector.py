import asyncio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from bleak import BleakClient
from scipy.stats import norm
import threading
import os
import signal
import time

# --- CONFIGURATION --- #
# Define ESP32 Mac Address And Nordic UART Service UUIDs
ESP32_ADDRESS = "90:15:06:94:73:0A" 
TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# --- GLOBAL STATE MANAGEMENT --- #
# Current Magnetometer Reading Value
current_reading = 0
# States: "CONNECTING", "CONNECTION_SUCCED", "CONNECTED", "FAILED"
connection_state = "CONNECTING"

def ble_callback(sender, data):
    """
    BLE Data Management
    Analyze Numeric Strings From ESP32 And Update Current Magnetometer Reading Value
    """
    global current_reading
    try:
        message = data.decode('utf-8').strip()
        if "NOT-DETECTED" in message:
            current_reading = 0
        else:         
            # Extract Numeric Payload From The String
            numeric_data = "".join(filter(str.isdigit, message))
            if numeric_data:
                current_reading = int(numeric_data)
    except Exception:
        pass

async def run_ble():
    """
    Main BLE ESP32 Connection Management
    Manage BLE Connection States To ESP32
    """
    global connection_state
    print(f"[BLE] Attempting connection to {ESP32_ADDRESS}...")
    try:
        # Connecting Attempt With 15 Seconds Timeout
        async with BleakClient(ESP32_ADDRESS, timeout=15.0) as client:
            
            # Connection Established
            connection_state = "CONNECTION_SUCCEEDED"
            print("[BLE] Connected!");

            # Wait 2 Seconds To Show Connected State Page
            await asyncio.sleep(2.0)

            # Main Mode         
            connection_state = "CONNECTED"
            await client.start_notify(TX_UUID, ble_callback)

            # Keep The Task Alive While The Plot Is Running
            while True:
                if not plt.fignum_exists(fig.number): break
                await asyncio.sleep(0.5)
                
    # Connection Issues
    except Exception as e:
        print(f"[BLE] Connection failed: {e}")
        connection_state = "FAILED"

def start_ble_thread():
    """
    Entry Point For Background BLE Management Thread
    """
    asyncio.run(run_ble())

def signal_handler(sig, frame):
    """
    Make Sure To Clean Process Termination On SIGINT (Ctrl + C)
    """
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)

# --- MATPLOTLIB VISUALIZATION SETUP --- #
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(10, 6))
# Calculate X-Axis Points For Gaussian Curve (0-2000)
x_axis = np.linspace(0, 2000, 1000)

def update_plot(frame):
    """
    Main Animation Loop
    Display And Update The Proper Plot Based On The Current Connection State
    """
    ax.clear()

    # --- SEARCHING STATE --- #
    if connection_state == "CONNECTING":
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.text(50, 55, "SEARCHING FOR ESP32 DEVICE...", fontsize=16, 
                color='gold', ha='center', fontweight='bold')
        ax.text(50, 40, "Wait or check if ESP32 is powered on", 
                fontsize=11, color='white', ha='center', style='italic')
        ax.axis('off')

    # --- CONNECTION ESTABLISHED STATE --- #
    elif connection_state == "CONNECTION_SUCCEEDED":
        ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis('off')
        ax.text(50, 60, "CONNECTED!", fontsize=24, color='lime', ha='center', fontweight='bold')
        ax.text(50, 40, "Loading...", fontsize=12, color='white', ha='center')

    # --- CONNECTION FAILED STATE --- #  
    elif connection_state == "FAILED":
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.text(50, 60, "CONNECTION FAILED!", fontsize=18, 
                color='red', ha='center', fontweight='bold')
        ax.text(50, 45, "Make sure Bluetooth is enabled on this device. Then:",
                fontsize=12, color='white', ha='center')
        ax.text(50, 35, "1. Close this program", 
                fontsize=12, color='white', ha='center')
        ax.text(50, 30, "2. Press the reset (EN) button on ESP32", 
                fontsize=12, color='white', ha='center')
        ax.text(50, 25, "3. Restart this program", 
                fontsize=12, color='white', ha='center')
        ax.axis('off')

    # --- LIVE METAL DETECTION RUNNING STATE --- #    
    elif connection_state == "CONNECTED":
        ax.axis('on')
        ax.set_xlim(0, 2000)
        ax.set_ylim(0, 100)
        ax.get_yaxis().set_visible(False)
        
        # Draw The Ferrous/Non-Ferrous Threshold Divider
        ax.axvline(50, color='white', linestyle='--', alpha=0.5)
        
        if current_reading > 0:

            # Non Ferrous Value
            if current_reading < 50:
                metal_type = 'NON-FERROUS'
                color = 'lime'
                # Highlight Non Ferrous Zone
                ax.axvspan(0, 50, color='lime', alpha=0.15)
            # Ferrous Value
            else:
                metal_type = 'FERROUS'
                color = 'red'
                # Highlight Ferrous Zone
                ax.axvspan(50, 2000, color='red', alpha=0.15)

            # Calculate And Enlarge Gaussian Bell Curve
            y = norm.pdf(x_axis, loc=current_reading, scale=15) * 2500
            ax.plot(x_axis, y, color=color, lw=3)
            ax.fill_between(x_axis, y, color=color, alpha=0.3)

            # Display Metal Type Label At The Center
            ax.text(1000, 85, metal_type, color=color, fontsize = 25,
                fontweight='bold', alpha=0.5, ha='center')
        
        ax.set_title(f"Live Analysis - Reading: {current_reading}", fontsize=14)
        ax.set_xlabel("Magnetic Intensity")
        ax.grid(True, alpha=0.1)

# Star the Background Thread To Manage BLE Communication
threading.Thread(target=start_ble_thread, daemon=True).start()

# --- MAIN EXECUTION SECTION --- #
try:
    # Set 10 FPS (100 ms interval) For Proper Live Plot Update
    anim = FuncAnimation(fig, update_plot, interval=100, cache_frame_data=False)
    plt.tight_layout()
    plt.show()

finally:
    # Print Program Closing Messages On Terminal
    print("[SYSTEM] ANALYSIS TERMINATED")
    print(">>> IN CASE OF CONNECTION ISSUES PRESS THE 'EN' BUTTON ON ESP32 <<<")
    print("\n")

    # Wait For BLE Driver Releasing Resources
    time.sleep(1.2)
    os._exit(0)

 
