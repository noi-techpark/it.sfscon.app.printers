#!/bin/bash
cd /home/pi/2023/sfscon/src/printer_station

# Replace 'your_program' with the command or path to the program you want to start.
COMMAND="./server.sh"

while true; do
  # Attempt to start the program.

  sleep 15;
  
  $COMMAND
  
  # Capture the exit code of the program.
  STATUS=$?
  
  # Check if the program started successfully.
  if [ $STATUS -eq 0 ]; then
    echo "Program has started successfully."
    break
  else
    echo "Failed to start the program. Retrying in 10 seconds..."
  fi
done