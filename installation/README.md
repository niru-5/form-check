# Setup

My setup consists of a linux machine which does not have a bluetooth module. I built the machine by buying multiple parts and I figured I won't be needing a bluetooth module for my home desktop. 
So, I went with running this on a raspberry pi. 

## Raspberry Pi Setup

I have tested this on a raspberry pi 5. and assume it mostly is the same for lower versions as well. 



### Install dependencies

From metawear repo, I have seen that it works best with python 3.7. So, I compiled the python 3.7 from source and that took quite some time, around 1-2 hours. 

```
sudo apt install -y \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    wget

cd /usr/src
sudo wget https://www.python.org/ftp/python/3.7.16/Python-3.7.16.tgz
sudo tar xzf Python-3.7.16.tgz
cd Python-3.7.16
sudo ./configure --enable-optimizations
sudo make -j$(nproc)
sudo make altinstall

python3.7 --version
```

some more dependencies

```
sudo apt-get install -y build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev

sudo apt update
sudo apt-get install -y build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev
sudo apt-get install bluetooth bluez libbluetooth-dev libudev-dev libboost-all-dev build-essential


```
setup a virtual environment

```
cd ~/
mkdir metawear 
cd metawear
python3.7 -m venv metawear_env
source metawear_env/bin/activate

pip3 install guizero

# this below package can take quite some time. I think it builds it from source.
pip3 install cassandra-driver 

```

Now, compile the metawear sdk from source

```
git clone --recurse-submodules --branch aarch64 https://github.com/mbientlab/MetaWear-SDK-Python.git
cd MetaWear-SDK-Python

# and then add a small line in the path MetaWear-SDK-Python/MetaWear-SDK-Cpp/src/metawear/dfu/cpp/json.hpp
# #pragma GCC diagnostic ignored "-Wmaybe-uninitialized"
# add the above line in the top along with the other pragmas.

python3 setup.py build
```


Now test the examples as shown in the readme of MetaWear-SDK-Python repo. 


Note: Sometimes, the bluetooth on rpi can be finicky, if you have issues with connecting to the sensor, use the below command to check if the bluetooth on rpi is working or not. 

```

bluetoothctl
scan on # it will show all the bluetooth devices around you. if you don't see a metawear sensor, then best to probably reboot or the folow the below steps

exit # to get back to the command line. 

sudo connmanctl enable bluetooth
sudo hciconfig hci0 down
sudo hciconfig hci0 up

sudo reboot
```