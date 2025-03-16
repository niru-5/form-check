#! /bin/bash

pi_ip=rpi5
# pi_folder=~/form-check/data_acquisition
location_on_pi=/home/rpi5/metawear/meta_wear_experiments

while true; do
    # Show a confirmation dialog
    zenity --question --text="Do you want to run the deploy script?" --width=300
    if [ $? -eq 0 ]; then
        # Proceed with the script if the user clicks "Yes"

        # Increment run_num in config.yaml
        run_num=$(grep 'run_num' config.yaml | awk '{print $2}')
        new_run_num=$((run_num + 1))
        echo "new_run_num: $new_run_num"
        sed -i "s/run_num: $run_num/run_num: $new_run_num/" config.yaml

        # Load run_name and run_num from config.yaml, removing any quotes
        run_name=$(grep 'run_name' config.yaml | awk '{print $2}' | sed 's/"//g')
        run_num=$(grep 'run_num' config.yaml | awk '{print $2}' | sed 's/"//g')
        run_num_str=$(printf "%s" "$run_num")  # Convert run_num to string
        run_directory=${run_name}_${run_num_str}

        # Copy all these files to the pi
        scp *.py $pi_ip:$location_on_pi
        scp config.yaml $pi_ip:$location_on_pi

        ssh -tt $pi_ip "cd $location_on_pi && source /home/rpi5/metawear/py37_env/bin/activate && PYTHONUNBUFFERED=1 python3 -u raw_data_logger.py config.yaml"

        # Copy the entire run directory from the Raspberry Pi
        scp -r $pi_ip:$location_on_pi/$run_directory data/

        # Delete the run directory on the Raspberry Pi
        ssh $pi_ip "cd $location_on_pi && rm -rf $run_directory"

        ssh $pi_ip "cd $location_on_pi && source /home/rpi5/metawear/py37_env/bin/activate && python3 reset_device.py config.yaml"

    else
        # Exit the script if the user clicks "No"
        exit 0
    fi
done