#!/usr/bin/env python3
import json
import time
import threading
import os
import sys
import signal

# Define the paths for the data files. These are now relative to the script's directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_FILE = os.path.join(BASE_DIR, "resources.json")
VILLAGERS_FILE = os.path.join(BASE_DIR, "villagers.json")
LOG_FILE = os.path.join(BASE_DIR, "game.log")  # Added log file
PID_FILE = os.path.join(BASE_DIR, "game.pid")  # Added pid file path, but we'll manage it ourselves

# Constants
TOTAL_VILLAGERS = 100
RESOURCE_TYPES = ["gold", "stone", "wood", "food"]
RESOURCE_PERCENTAGES = {
    "gold": 0.00004,  # 0.004%
    "stone": 0.90,    # 90%
    "wood": 0.001,    # 0.1%
    "food": 0.0001,    # 0.01%
}
UPDATE_INTERVAL = 10  # Seconds
MAX_LOG_SIZE = 20 * 1024 * 1024  # 20MB
BACKUP_LOG_SUFFIX = ".1" # Suffix for the rotated log file

# Ensure data files exist or create them
def ensure_data_files():
    """
    Ensures that the resources.json and villagers.json files exist.  If they
    don't, they are created with default data.  Handles potential file creation
    errors and logs them.
    """
    default_resources = {"gold": 0, "stone": 0, "wood": 0, "food": 0}
    default_villagers = {"gold": 0, "stone": 0, "wood": 0, "food": 0}

    for filename, default_data in [(RESOURCES_FILE, default_resources), (VILLAGERS_FILE, default_villagers)]:
        if not os.path.exists(filename):
            try:
                with open(filename, "w") as f:
                    json.dump(default_data, f, indent=4)
                log_message(f"Created {filename}")
            except Exception as e:
                log_message(f"Error creating {filename}: {e}")
                sys.exit(1)  # Exit if critical data file can't be created.

def load_resources():
    """
    Loads the resource data from resources.json.  Handles file loading errors.
    """
    try:
        with open(RESOURCES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_message(f"Error loading resources: {e}.  Returning default resources.")
        return {"gold": 0, "stone": 0, "wood": 0, "food": 0}  # Return default, don't crash.

def save_resources(resources):
    """
    Saves the resource data to resources.json.  Handles file saving errors.
    """
    try:
        with open(RESOURCES_FILE, "w") as f:
            json.dump(resources, f, indent=4)
    except Exception as e:
        log_message(f"Error saving resources: {e}")

def load_villagers():
    """
    Loads the villager data from villagers.json. Handles file loading errors.
    """
    try:
        with open(VILLAGERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_message(f"Error loading villagers: {e}.  Returning default villagers.")
        return {"gold": 0, "stone": 0, "wood": 0, "food": 0} #return default, don't crash

def save_villagers(villagers):
    """
    Saves the villager data to villagers.json. Handles file saving errors.
    """
    try:
        with open(VILLAGERS_FILE, "w") as f:
            json.dump(villagers, f, indent=4)
    except Exception as e:
        log_message(f"Error saving villagers: {e}")

def log_message(message):
    """
    Logs messages to the console and the log file.  Includes a timestamp.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - {message}\n"
    print(log_entry, end="")  # Keep output clean.
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to log file: {e}") # Print to standard error

def rotate_log_file():
    """
    Rotates the log file if it exceeds the maximum size.
    """
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
        backup_file = LOG_FILE + BACKUP_LOG_SUFFIX
        if os.path.exists(backup_file):
            os.remove(backup_file)  # Remove the old backup
        os.rename(LOG_FILE, backup_file)  # Rename current log to backup
        log_message(f"Rotated log file.  New log file: {LOG_FILE}")

def update_resources(resources, villagers):
    """
    Updates the resource amounts based on the number of villagers assigned
    to each resource type.
    """
    for resource_type in RESOURCE_TYPES:
        num_villagers = villagers[resource_type]
        # Calculate the resource gain for this type.
        resource_gain = num_villagers * RESOURCE_PERCENTAGES[resource_type]
        # Ensure resource gain is not negative
        if resource_gain < 0:
            resource_gain = 0
        resources[resource_type] += resource_gain
        # Log the resource update with high precision.
        log_message(f"Updated {resource_type}: +{resource_gain:.18f} (Villagers: {num_villagers})")
        rotate_log_file() #rotate log after writing

def game_loop(resources, villagers):
    """
    Main game loop that runs every UPDATE_INTERVAL seconds.  Now takes resources and villagers as arguments.
    """
    while True:
        update_resources(resources, villagers)
        save_resources(resources)
        time.sleep(UPDATE_INTERVAL)

def handle_command(command, resources, villagers):
    """
    Handles player commands to allocate villagers to resources, get status,
    and display help.
    """
    parts = command.split()
    if not parts:
        return  # Empty input, do nothing

    action = parts[0].lower()

    if action == "get":
        if len(parts) < 3:
            log_message("Invalid command format. Use: get <resource> with <number> villagers/villager")
            return

        resource_type = parts[1].lower()
        try:
            num_villagers = int(parts[3])  # Get the number directly
        except ValueError:
            log_message("Invalid number of villagers.  Must be an integer.")
            return

        if resource_type not in RESOURCE_TYPES:
            log_message(f"Invalid resource type: {resource_type}.  Must be one of {', '.join(RESOURCE_TYPES)}.")
            return

        current_total_villagers = sum(villagers.values())
        if current_total_villagers - villagers[resource_type] + num_villagers > TOTAL_VILLAGERS:
            log_message(f"Too many villagers. You have {current_total_villagers} villagers assigned. You can assign a maximum of {TOTAL_VILLAGERS}.")
            return

        villagers[resource_type] = num_villagers
        save_villagers(villagers)
        log_message(f"Set {num_villagers} villagers to {resource_type}.")

    elif action == "status":
        total_gathering_villagers = sum(villagers.values())  # Calculate total gathering villagers
        log_message(f"Current Resources: {json.dumps(resources, indent=4)}")
        log_message(f"Villager Allocation: {json.dumps(villagers, indent=4)}")
        log_message(f"Total Gathering Villagers: {total_gathering_villagers}") #display the total

    elif action == "help":
        log_message("Available commands:")
        log_message("  get <resource> with <number> villagers/villager - Assign villagers to a resource (e.g., get gold with 10 villagers)")
        log_message("  status - Display current resource levels and villager allocation")
        log_message("  help - Display this help message")
        log_message("  exit - Exit the game") #added exit to help

    elif action == "exit": #added exit command
        log_message("Exiting game.")
        sys.exit(0)

    else:
        log_message(f"Unknown command: {action}. Type 'help' for available commands.")

def daemonize():
    """
    Daemonizes the current process using standard Unix techniques.  This is
    less integrated with systemd, but it's a more traditional way to run
    a process in the background.
    """
    if os.name != 'posix':
        print("Daemonize is only supported on POSIX systems (Linux, macOS).")
        return False  # Indicate failure

    # Fork once.
    try:
        pid = os.fork()
        if pid > 0:
            # Exit the parent process.
            print(f"Daemon process ID: {pid}")  # Print PID to standard output
            with open(PID_FILE, "w") as f:
                f.write(str(pid))
            sys.exit(0)
        elif pid < 0:
            raise OSError(f"fork failed: {pid}")
    except OSError as e:
        print(f"fork #1 failed: {e}")
        return False

    # Become session leader and detach from controlling terminal.
    os.setsid()
    os.umask(0)

    # Fork again (optional, for complete detachment).
    try:
        pid = os.fork()
        if pid > 0:
            # Exit the first child.
            sys.exit(0)
        elif pid < 0:
            raise OSError(f"fork failed: {pid}")
    except OSError as e:
        print(f"fork #2 failed: {e}")
        return False

    # Redirect standard file descriptors.  This is crucial for a daemon.
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    # si.close() #not needed
    # so.close() #not needed
    # se.close() #not needed
    return True #Indicate success

def main(is_daemon=False): # Added is_daemon parameter
    """
    Main function to start the game.  Ensures data files exist, loads initial
    data, starts the game loop in a separate thread, and handles user input
    in the main thread.
    """
    ensure_data_files()
    resources = load_resources()
    villagers = load_villagers()

    # Print welcome message
    log_message("Welcome to the Resource Management Game!")
    log_message("Type 'help' to see available commands.")

    # Start the game loop in a separate thread, passing in resources and villagers
    game_thread = threading.Thread(target=game_loop, args=(resources, villagers))
    game_thread.daemon = True  # Allow the main thread to exit
    game_thread.start()

    # Main thread handles user input, only if not a daemon
    if not is_daemon:
        try:
            while True:
                command = input("Enter command: ").strip()
                handle_command(command, resources, villagers)
        except KeyboardInterrupt:
            log_message("Exiting game.  Cleaning up...")
            #  Add any cleanup here, if needed
            log_message("Game exited.")
        except Exception as e:
            log_message(f"An unexpected error occurred: {e}")
            log_message("Game exited due to error.")
    else:
        # If it is a daemon, just keep the game loop running
        while True:
            time.sleep(UPDATE_INTERVAL)
        

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        if daemonize(): #only start the game if the daemonize was successful
            main(is_daemon=True) # Pass the is_daemon flag
        else:
            print("Failed to daemonize.  Exiting.")
            sys.exit(1)
    else:
        #check if the game is already running
        try:
            with open(PID_FILE, "r") as f: # Use the defined PID_FILE
                pid = int(f.read())
                #check if the process exists
                if os.kill(pid, 0) == True:
                    print(f"Game is already running with PID {pid}.")
                    sys.exit(1)
        except FileNotFoundError:
            pass #if the file doesnt exist, the game is not running
        except ProcessLookupError:
            pass
        main()
