
from multiprocessing import Pool
from multiprocessing.context import TimeoutError

import rasp
from rasp.modelrun.grib.download import GribException
from rasp.common.logging import log_exception
from rasp.common.system import wait

def do_work(download_item):
    logger = rasp.modelrun.grib.get_logger()
    try:
        wait(5)
        result = { 'item': download_item, 'success': False }
        logger.debug("Worker process started [{0}]".format(download_item.filename))
        while not download_item.is_available():
            wait(60)
            logger.debug("Process[{0}] - Check file available".format(download_item.filename))
        result['success'] = download_item.download()
    except KeyboardInterrupt:
        logger.debug("Worker process interrupted by user [{0}]".format(download_item.filename))
        pass
    except Exception as e:
        log_exception("Downloading {0} failed", e, logger)
        pass
    return result

def download_all(grib_download_list, logger=rasp.modelrun.grib.get_logger()):

    configuration = rasp.modelrun.get_configuration()

    # make the Pool of workers
    pool = Pool(processes = configuration.grib.max_downloads) 

    #remove items already downloaded
    grib_must_download_list = []
    for grib_download_item in grib_download_list:
        if not grib_download_item.downloaded:
            grib_must_download_list.append(grib_download_item)

    if len(grib_must_download_list) == 0:
        logger.info("All grib files already downloaded")
        return

    results = pool.map_async(do_work, grib_must_download_list)
    raise_error = False
    try:
        for result in results.get(timeout = configuration.grib.max_wait_mins * 60):
            if result['success']:
                logger.info("file: {0}, status: SUCCESS".format(result['item'].filename))
            else:
                logger.error("file: {0}, status: ERROR".format(result['item'].filename))
                raise_error = True
    except TimeoutError as e:
        raise GribException("Download did not finish in alocated time")
    except KeyboardInterrupt:
        raise GribException("Download interrupted by user")
    finally:
        pool.close()
        pool.terminate()

    if raise_error == True:
        raise GribException("One or more downloads failed")