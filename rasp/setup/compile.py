import os
import logging
import urllib.parse
import subprocess
import shutil
import asyncio
from subprocess import CalledProcessError

from rasp.setup.configuration import CompileConfiguration
from rasp.common.download import download_file
from rasp.common.logging import start_file_log, stop_file_log

logger = logging.getLogger('rasp.compile')

class CompileException(Exception):
    pass

configuration = CompileConfiguration()

def chdir(path):
    logger.debug("Working path: {0}".format(path))
    os.chdir(path)

# function initializes tests path
# test sources are downloaded and extracted in this folder
def init_tests_path():
    tests_path = os.path.join(configuration.compile_path, 'TESTS')
    if not os.path.exists(tests_path):
        os.makedirs(tests_path)
    return tests_path

# function initializes libraries path
# libraries sources are downloaded and extracted in this folder
def init_libs_path():
    libs_path = os.path.join(configuration.compile_path, 'LIBRARIES')
    if not os.path.exists(libs_path):
        os.makedirs(libs_path)
    return libs_path

# function extracts filename from URL
def get_url_filename(url):
    logger.debug("Getting filename from {0}".format(url))
    url_parts = urllib.parse.urlparse(url)
    path_parts = url_parts.path.split('/')
    filename = path_parts[len(path_parts) - 1]
    logger.debug("filename = {0}".format(filename))
    return filename

# save current working path
cwd = os.getcwd()

# function downloads sources package to a file
def download_tar(url, path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        if urllib.parse.urlparse(url).scheme == '':
            #local file
            shutil.copyfile(os.path.join(os.path.dirname(__file__), 'libs', url), path)
        else:
            download_file(url, path)
    else:
        logger.debug("file {0} already downloaded".format(path))

# function executes scripting environment tests
# these tests verify necessary scripting programs are installed
def run_script_test(id, cmd, expected_output):
    logger.info('Test {0}'.format(id))
    try:
        logger.debug('Executing {0}'.format(cmd))
        output = str(subprocess.check_output(cmd.split(' ')))
        logger.debug("Output: {0}".format(output))
        if output.lower().find(expected_output.lower()) >= 0:
            logger.info("SUCCESS")
        else:
            logger.info("Test {0} failed".format(id))
            raise CompileException("Test {0} failed".format(id))
    except CompileException:
        raise
    except:
        raise CompileException("Test {0} failed".format(id))

# function sets compilation enviromental variables
def set_compile_env():
    os.environ["CC"] = 'gcc'
    os.environ["CXX"] = 'g++'
    os.environ["FC"] = 'gfortran'
    os.environ["FCFLAGS"] = '-m64'
    os.environ["F77"] = 'gfortran'
    os.environ["FFLAGS"] = '-m64'

# function sets NETCDF enviromental variable for WRF compilation
def set_netcdf_env():

    netcdf_config = configuration.libraries['netcdf']

    if (os.path.dirname(netcdf_config.inc_path) == os.path.dirname(netcdf_config.lib_path)):
        logger.debug("Setting NETCDF = {0}".format(os.path.dirname(netcdf_config.inc_path)))
        os.environ["NETCDF"] = os.path.dirname(netcdf_config.inc_path)
    else:
        libs_path = init_libs_path()
        netcdf_path = os.path.join(libs_path, 'netcdf')
        if not os.path.exists(netcdf_path):
            os.makedirs(netcdf_path)
        inc_link_path = os.path.join(netcdf_path, 'include')
        if not os.path.exists(inc_link_path):
            os.symlink(netcdf_config.inc_path, inc_link_path, True)
        lib_link_path = os.path.join(netcdf_path, 'lib')
        if not os.path.exists(lib_link_path):
            os.symlink(netcdf_config.lib_path, lib_link_path, True)
        logger.debug("Setting NETCDF = {0}".format(netcdf_path))
        os.environ["NETCDF"] = netcdf_path

# function sets JASPER enviromental variable for WPS compilation
def set_jasper_env():

    jasper_config = configuration.libraries['jasper']
    zlib_config = configuration.libraries['zlib']
    libpng_config = configuration.libraries['libpng']

    jasper_lib = jasper_config.lib_path
    if (jasper_config.lib_path != libpng_config.lib_path):
        jasper_lib += " -L{0}".format(libpng_config.lib_path)
    if (jasper_config.lib_path != zlib_config.lib_path):
        jasper_lib += " -L{0}".format(zlib_config.lib_path)
    os.environ["JASPERLIB"] = jasper_lib
    logger.debug("Setting JASPERLIB = {0}".format(jasper_lib))

    jasper_inc = jasper_config.inc_path
    if (jasper_config.inc_path != libpng_config.inc_path):
        jasper_inc += " -I{0}".format(libpng_config.inc_path)
    if (jasper_config.inc_path != zlib_config.inc_path):
        jasper_inc += " -I{0}".format(zlib_config.inc_path)
    os.environ["JASPERINC"] = jasper_inc
    logger.debug("Setting JASPERINC = {0}".format(jasper_inc))

def set_ld_library_path_env():
    if 'LD_LIBRARY_PATH' in os.environ:
        paths = os.environ["LD_LIBRARY_PATH"].split(':')
    else:
        paths = []

    for lib_config in configuration.libraries.values():
        if not lib_config.lib_path in paths:
            paths.append(lib_config.lib_path)
    logger.debug("Setting LD_LIBRARY_PATH = {0}".format(':'.join(paths)))
    os.environ["LD_LIBRARY_PATH"] = ':'.join(paths)


# function adds path to PATH enviromental variable
def add_path_env(path):
    os.environ["PATH"] = "{0}:{1}".format(path, os.environ["PATH"])

# function searched for a dir base on the beginning of the name 
# when found, reture full path to directory
def find_dir(path, dir_name_start):
    for name in os.listdir(path):
        item_path = os.path.join(path, name)
        if os.path.isdir(item_path) and name.startswith(dir_name_start):
            return item_path
    return None

# function verifies compiler programs are installed
def check_compilers():
    logger.debug('Checking compilers')
    compilers = ['gfortran', 'cpp', 'gcc', 'make', 'cmake']
    for c in compilers:
        try:
            output = subprocess.check_output(['which', c])
        except CalledProcessError:
            raise CompileException("Compiler {0} not installed".format(c))

        if output == '':
            raise CompileException("Compiler {0} not installed".format(c))
    # TODO check gcc version


# function executes a compilation system environment test
def run_compile_test(id, commands, expected_output, verify_cmd='./a.out'):
    logger.info('Test {0}'.format(id))
    for cmd in commands:
        logger.debug('Executing {0}'.format(cmd))
        subprocess.run(cmd.split(' '))
    try:
        output = str(subprocess.check_output(verify_cmd.split(' ')))
        logger.debug("Output: {0}".format(output))
        if output.find(expected_output) >= 0:
            logger.info("SUCCESS")
        else:
            logger.info("Test {0} failed".format(id))
            raise CompileException("Test {0} failed".format(id))
    except CompileException:
        raise
    except:
        raise CompileException("Test {0} failed".format(id))

# function executes compilation system environment tests
# these tests verify necessary compiler programs are installed
# uses run_compile_test to execute individual compiler tests
def run_system_environment_tests():
    tests_path = init_tests_path()

    logger.info('Test fortran compiler')
    download_path = os.path.join(tests_path, get_url_filename(configuration.tests.system_environment.sources_url))
    download_tar(configuration.tests.system_environment.sources_url, download_path)
    chdir(tests_path)
    logger.debug('Extracting {0}'.format(download_path))
    subprocess.check_output(['tar', '-xf', download_path])
    run_compile_test(1, ['gfortran TEST_1_fortran_only_fixed.f'], 'SUCCESS test 1 fortran only fixed format')
    run_compile_test(2, ['gfortran TEST_2_fortran_only_free.f90'], 'SUCCESS test 2 fortran only free format')
    run_compile_test(3, ['gcc TEST_3_c_only.c'], 'SUCCESS test 3 C only')
    run_compile_test(
        4,
        ['gcc -c -m64 TEST_4_fortran+c_c.c',
            'gfortran -c -m64 TEST_4_fortran+c_f.f90',
            'gfortran -m64 TEST_4_fortran+c_f.o TEST_4_fortran+c_c.o'],
        'SUCCESS test 4 fortran calling c')

    logger.info('Test scripting compiler')
    run_script_test(1, './TEST_csh.csh', 'SUCCESS csh test')
    run_script_test(2, './TEST_perl.pl', 'SUCCESS perl test')
    run_script_test(3, './TEST_sh.sh', 'SUCCESS sh test')

# function executes library compatibility compilation tests
# these tests verify dependent libraries are installed
def run_library_compatibility_tests():
    tests_path = init_tests_path()

    logger.info('Test Library Compatibility')

    download_path = os.path.join(tests_path, get_url_filename(configuration.tests.lib_compatibity.sources_url))
    download_tar(configuration.tests.lib_compatibity.sources_url, download_path)
    chdir(tests_path)
    logger.debug('Extracting {0}'.format(download_path))
    subprocess.check_output(['tar', '-xf', download_path])

    set_compile_env()
    set_netcdf_env()
    set_ld_library_path_env()

    shutil.copyfile(os.path.join(os.environ["NETCDF"], 'include/netcdf.inc'), os.path.join(tests_path, 'netcdf.inc'))
    run_compile_test(
        1,
        ['gfortran -c 01_fortran+c+netcdf_f.f',
            'gcc -c 01_fortran+c+netcdf_c.c',
            'gfortran 01_fortran+c+netcdf_f.o 01_fortran+c+netcdf_c.o -L{NETCDF}/lib -lnetcdff -lnetcdf'.format(NETCDF=os.environ["NETCDF"])],
            'SUCCESS test 1 fortran + c + netcdf')
    #run_compile_test(
    #    2,
    #    ['mpif90 -c 02_fortran+c+netcdf+mpi_f.f',
    #        'mpicc -c 02_fortran+c+netcdf+mpi_c.c',
    #        'mpif90 02_fortran+c+netcdf+mpi_f.o 02_fortran+c+netcdf+mpi_c.o -L{NETCDF}/lib -lnetcdff -lnetcdf'.format(NETCDF=os.environ["NETCDF"])],
    #        'SUCCESS test 2 fortran + c + netcdf + mpi',
    #        verify_cmd='mpirun ./a.out')

def run_make_install(make_cmd = None):
    if not make_cmd:
        make_cmd = 'make'
    logger.debug("Running {0}".format(make_cmd))
    with open('make.log', 'wt') as f:
        subprocess.run(make_cmd.split(' '), check=True, stderr=subprocess.STDOUT, stdout=f)
    logger.debug("Running make install")
    with open('make.install.log', 'wt') as f:
        subprocess.run(['make', 'install'], check=True, stderr=subprocess.STDOUT, stdout=f)


# function executes configure and make in current directory
def run_config_make(configure_cmd):
    logger.debug("Running {0}".format(configure_cmd))
    with open('configure_cmd.log', 'wt') as f:
        subprocess.run(configure_cmd.split(' '), check=True, stderr=subprocess.STDOUT, stdout=f)
    run_make_install()

# function executes compile in current directory
def run_compile(compile_cmd):
    logger.debug("Running {0}".format(compile_cmd))
    with open('compile.log', 'wt') as f:
        subprocess.run(compile_cmd.split(' '), check=True, stderr=subprocess.STDOUT, stdout=f)

def run_cmake(source_dir, build_dir, install_dir):
    cmd_args = [
        'cmake',
        '-G',
        'Unix Makefiles',
        '-H{source_dir}'.format(source_dir = source_dir),
        '-B{build_dir}'.format(build_dir = build_dir),
        '-DCMAKE_INSTALL_PREFIX={install_dir}'.format(install_dir = install_dir)
        ]

    logger.debug("Running {0}".format(' '.join(cmd_args)))
    with open('cmake.log', 'wt') as f:
        subprocess.run(cmd_args, check=True, stderr=subprocess.STDOUT, stdout=f)

def compile_lib(libs_path, lib_build_path, name, url, clean = False, config_args = None, cmake = False):
    logger.info('Compiling {0}'.format(name))
    logger.debug('lib_build_path {0}'.format(lib_build_path))
    logger.debug('url {0}'.format(url))
    logger.debug('config_args {0}'.format(config_args))
    download_path = os.path.join(libs_path, get_url_filename(url))

    # check if we can skip building
    if not clean and os.path.exists("{0}.ok".format(download_path)):
        logger.info('{0} already built'.format(name))
    else:
        if os.path.exists("{0}.ok".format(download_path)):
            os.remove("{0}.ok".format(download_path))

        # remove all dirs starting with "name"
        while True:
            path = find_dir(libs_path, name)
            if path:
                shutil.rmtree(path)
            else:
                break

        chdir(libs_path)
        # download sources TAR
        download_tar(url, download_path)
        # exctract TAR
        subprocess.check_output(['tar', 'xvzf', download_path])
        # find and go to netcdf dir
        chdir(find_dir(libs_path, name))
        if cmake:
            source_dir = find_dir(libs_path, name)
            source_build_dir = "{0}-build".format(source_dir)
            run_cmake(source_dir, source_build_dir, lib_build_path)
            chdir(source_build_dir)
            run_make_install('make clean all')
        else:
            # run config and make
            str_config_args = ""
            if config_args:
                str_config_args = " {0}".format(" ".join(config_args))
            run_config_make('./configure --prefix={0}{1}'.format(lib_build_path, str_config_args))

        # indicate successfull compilation
        open("{0}.ok".format(download_path), 'a').close()

        # add_path_env(os.path.join(libs_path, 'netcdf/bin'))
        chdir(libs_path)

def compile_libraries(clean = False):
    libs_path = init_libs_path()

    os.environ["CPPFLAGS"] = ''
    os.environ["LDFLAGS"] = ''

    set_compile_env()

    for lib_name, lib_config in configuration.libraries.items():
        if lib_config.compile:
            # modify configuration to reflect where lib is built
            lib_build_path = os.path.join(libs_path, lib_name)
            if lib_config.prefix:
                lib_build_path = os.path.join(libs_path, lib_config.prefix)
            lib_config.inc_path = os.path.join(lib_build_path, 'include')
            lib_config.lib_path = os.path.join(lib_build_path, 'lib')
            compile_lib(libs_path, lib_build_path, lib_name, lib_config.sources_url, clean = clean, config_args = lib_config.configure_options, cmake = lib_config.cmake)
            if os.environ["CPPFLAGS"] != '':
                os.environ["CPPFLAGS"] += " -I{0}/include".format(lib_build_path)
                os.environ["LDFLAGS"] += " -L{0}/lib".format(lib_build_path)
            else:
                os.environ["CPPFLAGS"] = "-I{0}/include".format(lib_build_path)
                os.environ["LDFLAGS"] = "-L{0}/lib".format(lib_build_path)

def get_lib_paths():
    libs_path = init_libs_path()
    lib_paths = set()
    for lib_name, lib_config in configuration.libraries.items():
        if lib_config.compile:
            if lib_config.prefix:
                lib_paths.add(os.path.join(libs_path, lib_config.prefix, 'lib'))
            else:
                lib_paths.add(os.path.join(libs_path, lib_name, 'lib'))
        else:
            lib_paths.add(lib_config.lib_path)
    return list(lib_paths)


# function executes configure for WRF and WPS
# passing in configuration options
async def run_wrf_wps_configure(options, timeout=5):
    process = await asyncio.create_subprocess_exec('./configure', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, stdin=asyncio.subprocess.PIPE)

    for op in options:
        while True:
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout)
                #print(line.strip().decode())
            except asyncio.TimeoutError:
                break
        input = "{0}\n".format(op)
        logger.debug("sending input: {0}".format(input.strip()))
        process.stdin.write(input.encode())

    with open('configure.log', "wb") as f:
        while not process.stdout.at_eof():
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout)
                f.write(line)
                print(line.strip().decode())
            except asyncio.TimeoutError:
                process.kill()
                break
        f.write(b'loop exit\n')
    await process.wait()

# function builds WRF
def compile_wrf(clean = False):
    logger.info('Compiling WRF')

    ok_file_path = os.path.join(configuration.compile_path, 'wrf.ok')
    wrf_path = os.path.join(configuration.compile_path, 'WRF')
    download_path = os.path.join(configuration.compile_path, 'wrf.tar.gz')
    download_tar(configuration.wrf.sources_url, download_path)

    # check if we can skip building
    if not clean and os.path.exists(ok_file_path):
        logger.info('WRF already built')
    else:
        if os.path.exists(ok_file_path):
            os.remove(ok_file_path)

        # remove all dirs starting with "name"
        while True:
            path = find_dir(configuration.compile_path, 'WRF')
            if path:
                shutil.rmtree(path)
            else:
                break

        set_compile_env()
        set_netcdf_env()
        set_jasper_env()

        chdir(configuration.compile_path)
        logger.debug("Extracting {0}".format(download_path))
        subprocess.check_output(['tar', 'xvzf', download_path])
        os.rename(find_dir(configuration.compile_path, 'WRF'), wrf_path)
        chdir(wrf_path)
        subprocess.check_output(['./clean'])

        if configuration.auto_answer:
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run_wrf_wps_configure([configuration.wrf.options_compile_configuration, configuration.wrf.options_nesting], timeout=3))
            loop.close()
        else:
            subprocess.check_output(['./configure'])

        run_compile('./compile em_real')
        if not os.path.exists(os.path.join(os.getcwd(), 'main/wrf.exe')):
            raise CompileException('wrf.exe not found')
        if not os.path.exists(os.path.join(os.getcwd(), 'main/real.exe')):
            raise CompileException('real.exe not found')
        if not os.path.exists(os.path.join(os.getcwd(), 'main/ndown.exe')):
            raise CompileException('ndown.exe not found')
        logger.info("Compile SUCCESS")

        # indicate successfull compilation
        open(ok_file_path, 'a').close()

# function builds WRF
def compile_wps(clean = False):
    logger.info('Compiling WPS')

    ok_file_path = os.path.join(configuration.compile_path, 'wps.ok')
    wps_path = os.path.join(configuration.compile_path, 'WPS')
    download_path = os.path.join(configuration.compile_path, 'wps.tar.gz')
    download_tar(configuration.wps.sources_url, download_path)

    # check if we can skip building
    if not clean and os.path.exists(ok_file_path):
        logger.info('WPS already built')
    else:
        if os.path.exists(ok_file_path):
            os.remove(ok_file_path)

        # remove all dirs starting with "name"
        while True:
            path = find_dir(configuration.compile_path, 'WPS')
            if path:
                shutil.rmtree(path)
            else:
                break

        set_compile_env()
        set_netcdf_env()
        set_jasper_env()

        chdir(configuration.compile_path)
        subprocess.check_output(['tar', 'xvzf', download_path])
        os.rename(find_dir(configuration.compile_path, 'WPS'), wps_path)
        chdir(wps_path)
        subprocess.check_output(['./clean'])

        if configuration.auto_answer:
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run_wrf_wps_configure([configuration.wps.options_compile_configuration], timeout=3))
            loop.close()
        else:
            logger.info('running ./configure')
            subprocess.run(['./configure'], check=True)

        # http://forum.wrfforum.com/viewtopic.php?f=20&t=5672
        shutil.copyfile('configure.wps', 'configure.wps.bak')
        with open('configure.wps.bak', 'rt') as fin:
            with open('configure.wps', 'wt') as fout:
                for line in fin:
                    if line.endswith('-lnetcdf\n'):
                        line = line.replace('-lnetcdf\n', '-lnetcdf -lgomp\n')
                    fout.write(line)

        run_compile('./compile')

        if not os.path.exists(os.path.join(os.getcwd(), 'geogrid/src/geogrid.exe')):
            raise CompileException('geogrid.exe not found')
        if not os.path.exists(os.path.join(os.getcwd(), 'ungrib/src/ungrib.exe')):
            raise CompileException('ungrib.exe not found')
        if not os.path.exists(os.path.join(os.getcwd(), 'metgrid/src/metgrid.exe')):
            raise CompileException('metgrid.exe not found')

        logger.info("Compile SUCCESS")

        # indicate successfull compilation
        open(ok_file_path, 'a').close()


def compile(clean = True):
    # initialize compile path
    logger.debug('Creating compile directory')
    # WRF and WPS sources are downloaded and extracted in this folder
    if not os.path.exists(configuration.compile_path):
        os.makedirs(configuration.compile_path)

    handler = start_file_log(logger, os.path.join(configuration.compile_path, 'compile.log.csv'))

    check_compilers()
    
    try:
        if (configuration.tests.system_environment.enabled):
            run_system_environment_tests()
        compile_libraries(clean = clean)
        if (configuration.tests.lib_compatibity.enabled):
            run_library_compatibility_tests()

        compile_wrf(clean = clean)
        compile_wps(clean = clean)
    except Exception as e:
        logger.error(e)
        raise

    finally:
        os.chdir(cwd)
        stop_file_log(logger, handler)

if __name__ == '__main__':
    compile(clean=False)
