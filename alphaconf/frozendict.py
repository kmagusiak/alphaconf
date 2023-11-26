# Performance of this small dict is enough for most cases.
# Only when the dict becomes big, the copy strategy is slower after the
# dict contains over a few hundred of elements. So we'll keep it simple,
# hence the primary usage is for small contextual information.


class FrozenDict(dict):
    """Immutable dict based on a dict() implementation"""

    def _immutable(self, *a, **kw):
        raise NotImplementedError('Immutable dict')

    update = _immutable  # type: ignore
    __setitem__ = _immutable  # type: ignore
    __delitem__ = _immutable  # type: ignore
    setdefault = _immutable  # type: ignore
    update = _immutable  # type: ignore
    clear = _immutable  # type: ignore
    pop = _immutable  # type: ignore
    popitem = _immutable  # type: ignore

    def __repr__(self):
        return 'frozendict' + super().__repr__()

    def __str__(self):
        return super().__repr__()

    @classmethod
    def fromkeys(cls, it, v=None):
        return FrozenDict((i, v) for i in it)

    def __or__(self, value):
        return FrozenDict({**self, **value})

    def __ror__(self, value):
        return FrozenDict({**value, **self})

    __ior__ = _immutable  # type: ignore


frozendict = FrozenDict
__all__ = ['frozendict']
