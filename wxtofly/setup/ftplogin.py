import os
import netrc

def add_ftp_login(server, username, password):
    netrc_path =os.path.expanduser('~/.netrc')
    if os.path.exists(netrc_path):
        user_netrc = netrc.netrc(netrc_path)
        user_netrc.hosts[server] = (username, None, password)
        with open(netrc_path, "wt") as f:
            for h in user_netrc.hosts:
                f.write('machine {0} login {1} password {2}\n'.format(h, user_netrc.hosts[h][0], user_netrc.hosts[h][2]))

    else:
        with open(netrc_path, "wt") as f:
            f.write('machine {0} login {1} password {2}\n'.format(server, username, password))
