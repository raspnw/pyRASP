import matplotlib.pyplot as plt
import netCDF4

def netCDF_to_image(path, var_name, time=0):
    # open a local NetCDF file or remote OPeNDAP URL
    nc = netCDF4.Dataset(path)
    var = nc.variables[var_name]
    # make image
    plt.figure(figsize=(10,10))
    plt.imshow(var[time],origin='lower') 
    plt.title(var.description)
    plt.savefig("{0}.png".format(path), bbox_inches=0)
    nc.close()
