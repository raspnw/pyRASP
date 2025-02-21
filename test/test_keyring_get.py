import os
import keyring

service_id = 'RASP'
print(keyring.get_password(service_id, 'dustin'))