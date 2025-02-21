
import os
import netrc

if __name__ == '__main__':

    netrc_path =os.path.expanduser('~/.netrc')
    print(netrc_path)

    if os.path.exists(netrc_path):
        user_netrc = netrc.netrc(netrc_path)
        print(user_netrc.__repr__())
        print(user_netrc.hosts['wxtofly.net'][0])
        print(user_netrc.hosts['wxtofly.net'][1])
        print(user_netrc.hosts['wxtofly.net'][2])

    else:
        with open(netrc_path, "wt") as f:
            f.write('machine {0} login {1} password {2}\n'.format('wxtofly.net', 'olneytj', 'tigermt56&'))

