import serial
import sys
import time

def main():
    if len(sys.argv) < 4:
        print("Usage: python spi_tool.py <PORT> <COMMAND> [ARGS...]")
        print("Commands:")
        print("  id - Identify chip")
        print("  dump <filename> <size_in_kb> - Dump flash to file")
        print("  flash <filename> - Flash file to chip")
        print("  erase - Erase the entire chip")
        return

    port = sys.argv[1]
    command = sys.argv[2]

    try:
        ser = serial.Serial(port, 921600, timeout=1)
    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
        return

    time.sleep(2) # Wait for the board to reset

    if command == "id":
        ser.write(b'I')
        jedec_id = ser.read(3)
        if jedec_id:
            print(f"JEDEC ID: {jedec_id.hex()}")
        else:
            print("No response from chip.")

    elif command == "dump":
        if len(sys.argv) != 5:
            print("Usage: python spi_tool.py <PORT> dump <filename> <size_in_kb>")
            return
        filename = sys.argv[3]
        size_kb = int(sys.argv[4])
        total_bytes = size_kb * 1024
        
        with open(filename, 'wb') as f:
            for addr in range(0, total_bytes, 256):
                ser.write(f'R{addr},256,'.encode())
                data = ser.read(256)
                f.write(data)
                progress = (addr + 256) / total_bytes * 100
                print(f"Dumping... {progress:.2f}% complete", end='\r')
        print("\nDump complete.")

    elif command == "flash":
        if len(sys.argv) != 4:
            print("Usage: python spi_tool.py <PORT> flash <filename>")
            return
        filename = sys.argv[3]
        
        with open(filename, 'rb') as f:
            addr = 0
            while True:
                chunk = f.read(256)
                if not chunk:
                    break
                ser.write(f'W{addr},{len(chunk)},'.encode())
                ser.write(chunk)
                time.sleep(0.01) # Give the chip some time to write
                addr += len(chunk)
                progress = (addr / f.tell()) * 100 if f.tell() > 0 else 0
                print(f"Flashing... {progress:.2f}% complete", end='\r')
        print("\nFlash complete.")

    elif command == "erase":
        print("Erasing chip... this may take some time.")
        ser.write(b'E')
        time.sleep(6) # Wait for erase
        print("Erase command sent.")

    else:
        print(f"Unknown command: {command}")

    ser.close()

if __name__ == "__main__":
    main()
