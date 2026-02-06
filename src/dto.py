import json
from dataclasses import dataclass, field, is_dataclass, asdict, fields as dc_fields, MISSING
from typing import Any, Callable, cast, Generic, TypeVar, overload
from conf import ks, Optional
from util import log

from dtom import Ausl, Muod, Gpsk, Excl, Mrg

lg = log.get(__name__)

T = TypeVar('T')


_UNSET = object()

def fldDflt(fld):
    if fld.default is not MISSING: return fld.default
    if fld.default_factory is not MISSING: return fld.default_factory()
    return _UNSET

def cstv(fldType, val, default=_UNSET):
    if val is None: return default if default is not _UNSET else val
    if fldType is bool:
        if isinstance(val, str): return val.lower() in ('true', '1', 'yes', 'on')
        return bool(val)
    if fldType is int:
        if isinstance(val, bool): return default if default is not _UNSET else (1 if val else 0)
        if isinstance(val, int): return val
        try: return int(val) if val else (default if default is not _UNSET else 0)
        except (ValueError, TypeError): return default if default is not _UNSET else 0
    if fldType is float:
        if isinstance(val, bool): return default if default is not _UNSET else (1.0 if val else 0.0)
        if isinstance(val, (int, float)): return float(val)
        try: return float(val) if val else (default if default is not _UNSET else 0.0)
        except (ValueError, TypeError): return default if default is not _UNSET else 0.0
    if fldType is str:
        if not isinstance(val, str): return str(val)
    if is_dataclass(fldType):
        if isinstance(val, dict):
            vk = {f.name for f in dc_fields(fldType)}
            return cstd(fldType(**{k: v for k, v in val.items() if k in vk}))
        if is_dataclass(val): return cstd(val)
        return default if default is not _UNSET else fldType()
    return val


def cstd(dc):
    for fld in dc_fields(dc): setattr(dc, fld.name, cstv(fld.type, getattr(dc, fld.name), fldDflt(fld)))
    return dc


class DcProxy(Generic[T]):
    def __init__(self, dc: T, field: 'AutoDbField[Any]', owner: Any):
        object.__setattr__(self, '_dc', dc)
        object.__setattr__(self, '_field', field)
        object.__setattr__(self, '_owner', owner)

    def __getattr__(self, name: str) -> Any:
        dc = object.__getattribute__(self, '_dc')
        val = getattr(dc, name)
        for fld in dc_fields(dc):
            if fld.name == name: return cstv(fld.type, val, fldDflt(fld))
        return val

    def __setattr__(self, name: str, value: Any) -> None:
        dc = object.__getattribute__(self, '_dc')
        for fld in dc_fields(dc):
            if fld.name == name:
                value = cstv(fld.type, value)
                break
        setattr(dc, name, value)
        field: AutoDbField[Any] = object.__getattribute__(self, '_field')
        owner = object.__getattribute__(self, '_owner')
        field._saveToDb(owner, dc)

    def __str__(self) -> str: return str(object.__getattribute__(self, '_dc'))
    def __repr__(self) -> str: return repr(object.__getattribute__(self, '_dc'))

    def raw(self) -> T:
        return object.__getattribute__(self, '_dc')


class AutoDbField(Generic[T]):
    def __init__(self, key: str, cast_type: type[T], default: T | None=None):
        self.key = key
        self.cast_type: Callable[..., Any] = cast_type  # type: type[T], but used as callable
        if default is None and is_dataclass(cast_type): self.default = cast_type()
        else: self.default = default
        self._cache_key = f'_cache_{key}'

    @overload
    def __get__(self, instance: None, owner: type) -> 'AutoDbField[T]': ...
    @overload
    def __get__(self, instance: object, owner: type) -> T: ...
    def __get__(self, instance: Any, owner: Any) -> Any:
        import db.sets as sets
        if instance is None: return self
        if hasattr(instance, self._cache_key): return getattr(instance, self._cache_key)
        val = sets.get(self.key, self.default)
        if self.cast_type and val is not None:
            try:
                if self.cast_type is dict: val = json.loads(val) if isinstance(val, str) and val else self.default
                elif is_dataclass(self.cast_type):
                    data = json.loads(val) if isinstance(val, str) else val
                    if isinstance(data, dict):
                        vk = {f.name for f in dc_fields(self.cast_type)}
                        dc = cstd(cast(Any, self.cast_type)(**{k: v for k, v in data.items() if k in vk}))
                    else: dc = self.default
                    val = DcProxy(dc, cast(Any, self), instance)
                else: val = cstv(self.cast_type, val)
            except (ValueError, TypeError, json.JSONDecodeError):
                lg.error(f'[AutoDbField] Failed to convert {val} to {self.cast_type}, use default[{self.default}]')
                val = self.default
        return self._cache(instance, val)

    def __set__(self, instance, value):
        import db.sets as sets
        if isinstance(value, DcProxy): value = object.__getattribute__(value, '_dc')
        if self.cast_type and value is not None:
            try:
                if self.cast_type is dict: pass
                elif is_dataclass(self.cast_type) and is_dataclass(value): cstd(value)
                else: value = cstv(self.cast_type, value)
            except (ValueError, TypeError):
                lg.error(f'[AutoDbField] Failed to convert {value} to {self.cast_type} for key[{self.key}], use default[{self.default}]')
                value = self.default
        self._saveToDb(instance, value)
        self._cache(instance, value)

    def _cache(self, inst, val):
        if is_dataclass(self.cast_type) and not isinstance(val, DcProxy) and is_dataclass(val): val = DcProxy(val, cast(Any, self), inst)
        setattr(inst, self._cache_key, val)
        return val

    def _saveToDb(self, instance, value):
        import db.sets as sets
        if isinstance(value, DcProxy): value = object.__getattribute__(value, '_dc')
        if self.cast_type is dict: sets.save(self.key, json.dumps(value, ensure_ascii=False))
        elif is_dataclass(value): sets.save(self.key, json.dumps(asdict(cast(Any, value)), ensure_ascii=False))
        else: sets.save(self.key, str(value))


class DtoSets:
    tskFloat = AutoDbField('tskFloat', bool, False)

    pathImmich = AutoDbField('immich:Path', str, '')
    pathThumb = AutoDbField('immich:Thumb', str, '')
    pathLibs = AutoDbField('immich:Libs', dict, {})

    usrId = AutoDbField('usrId', str, '')

    photoQ = AutoDbField('photoQ', str, ks.db.thumbnail)
    thMin = AutoDbField('simMin', float, 0.93)

    autoNext = AutoDbField('autoNext', bool, True)
    showGridInfo = AutoDbField('showGridInfo', bool, True)

    rtree = AutoDbField('simRtree', bool, False)
    rtreeMax = AutoDbField('simMaxItems', int, 200)

    muod = AutoDbField('muod', Muod)
    gpsk = AutoDbField('gpsk', Gpsk)

    ausl = AutoDbField('ausl', Ausl)

    pathFilter = AutoDbField('pathFilter', str, '')

    excl = AutoDbField('excl', Excl)

    gpuAutoMode = AutoDbField('gpuAutoMode', bool, True)
    gpuBatchSize = AutoDbField('gpuBatchSize', int, 8)

    cpuAutoMode = AutoDbField('cpuAutoMode', bool, True)
    cpuWorkers = AutoDbField('cpuWorkers', int, 4)

    mrg = AutoDbField('mrg', Mrg)

    mdlImgSets = AutoDbField('mdlImgSets', dict, {'auto': False, 'help': True, 'info': True})

    def checkIsExclude(self, asset) -> bool:
        if not self.excl.on or not self.excl.filNam: return False
        if not asset or not asset.originalFileName: return False

        filters = [f.strip() for f in self.excl.filNam.split(',') if f.strip()]
        if not filters: return False

        fileName = asset.originalFileName.lower()

        for flt in filters:
            flt = flt.lower()
            if flt.startswith('.'):
                if fileName.endswith(flt): return True
            elif flt in fileName: return True

        return False

    @classmethod
    def get(cls, key, default=None):
        import db.sets as sets
        value = sets.get(key, default)
        return value

    @classmethod
    def save(cls, key, value):
        import db.sets as sets
        return sets.save(key, str(value))


    def clearCache(self):
        for attr_name in dir(self.__class__):
            attr = getattr(self.__class__, attr_name)
            if isinstance(attr, AutoDbField):
                cache_key = attr._cache_key
                if hasattr(self, cache_key): delattr(self, cache_key)

# global
dto = DtoSets()
