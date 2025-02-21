import os
import keyring

service_id = 'RASP'
keyring.set_password(service_id, 'dustin', 'my secret password')