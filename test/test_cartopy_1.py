import cartopy.crs as ccrs 
import cartopy.feature as cfeature
import matplotlib.pyplot as plt

import matplotlib
matplotlib.use('agg')
plt.ioff()

def main():
    fig = plt.figure(figsize=(20*4,5*4), dpi=100, frameon=False)
  #  ax = fig.add_subplot(1, 1, 1, projection=ccrs.Mercator())
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.LambertCylindrical())

    ax.set_extent([-180, 180, -20, 20],crs=ccrs.LambertCylindrical())

    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)
    plt.axis('off')

    plt.savefig('test.png', bbox_inches='tight', pad_inches=0)
    
if __name__ == '__main__':
    main()