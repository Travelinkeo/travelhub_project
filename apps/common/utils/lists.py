from itertools import islice


def chunk_list(iterable, size):
    it = iter(iterable)
    return iter(lambda: list(islice(it, size)), [])
