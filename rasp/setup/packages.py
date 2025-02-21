import apt
from rasp.setup import logger

def install_packages(packages):

    logger.debug("Installing packages: {0}".format(packages))

    cache = apt.cache.Cache()
    cache.update()

    install = False
    for pkg_name in packages:
        pkg = cache[pkg_name]
        if pkg.is_installed:
            logger.info("{pkg_name} already installed".format(pkg_name=pkg_name))
        else:
            install = True
            logger.debug("Marking package {0} for install".format(pkg_name))
            pkg.mark_install()

    if install:
        logger.debug("Installing packages")
        cache.commit()
