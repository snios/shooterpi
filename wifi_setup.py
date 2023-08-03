import subprocess

# Run commands to install required packages
subprocess.run(['sudo', 'apt', 'update'])
subprocess.run(['sudo', 'apt', 'install', 'hostapd', 'dnsmasq'])

# Configure network interfaces
with open('/etc/dhcpcd.conf', 'a') as file:
    file.write('interface wlan0\n')
    file.write('static ip_address=192.168.4.1/24\n')
    file.write('nohook wpa_supplicant\n')

# Configure DHCP server (dnsmasq)
with open('/etc/dnsmasq.conf', 'w') as file:
    file.write('interface=wlan0\n')
    file.write('dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h\n')
    file.write('domain=wlan\n')
    file.write('address=/gw.wlan/192.168.4.1\n')

# Configure access point (hostapd)
with open('/etc/hostapd/hostapd.conf', 'w') as file:
    file.write('interface=wlan0\n')
    file.write('ssid=Your_AP_SSID\n')
    file.write('hw_mode=g\n')
    file.write('channel=7\n')
    file.write('macaddr_acl=0\n')
    file.write('auth_algs=1\n')
    file.write('ignore_broadcast_ssid=0\n')
    file.write('wpa=2\n')
    file.write('wpa_passphrase=Your_Passphrase\n')
    file.write('wpa_key_mgmt=WPA-PSK\n')
    file.write('wpa_pairwise=TKIP\n')
    file.write('rsn_pairwise=CCMP\n')

# Modify hostapd default configuration
with open('/etc/default/hostapd', 'a') as file:
    file.write('DAEMON_CONF="/etc/hostapd/hostapd.conf"\n')

# Start services and enable them to run on boot
subprocess.run(['sudo', 'systemctl', 'unmask', 'hostapd'])
subprocess.run(['sudo', 'systemctl', 'enable', 'hostapd'])
subprocess.run(['sudo', 'systemctl', 'enable', 'dnsmasq'])

# Reboot the Raspberry Pi
subprocess.run(['sudo', 'reboot'])
