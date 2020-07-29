def timeit(method):
    def timed(*args, **kw):

        result = None
        try:
            ts = time.time()
            result = method(*args, **kw)
            te = time.time()
        except Exception:
            logger.exception('')
        if result is not None:
            logger.info('{}: {:.2f} s'.format(method.__name__, te - ts))
            return result
    return timed