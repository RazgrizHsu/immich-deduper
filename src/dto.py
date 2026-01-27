import json
from dataclasses import dataclass, is_dataclass, asdict, fields as dc_fields
from typing import Any, Callable, cast, Generic, TypeVar, overload
from conf import ks, Optional
from util import log

lg = log.get(__name__)

T = TypeVar('T')


def _castVal(fldType, val):
    if fldType is bool and isinstance(val, str):
        return val.lower() in ('true', '1', 'yes', 'on')
    elif fldType is int and not isinstance(val, int):
        return int(val) if val else 0
    elif fldType is float and not isinstance(val, (int, float)):
        return float(val) if val else 0.0
    return val


def _castDc(dc):
    for fld in dc_fields(dc):
        setattr(dc, fld.name, _castVal(fld.type, getattr(dc, fld.name)))
    return dc


class DcProxy:
    def __init__(self, dc: Any, field: 'AutoDbField[Any]', owner: Any):
        object.__setattr__(self, '_dc', dc)
        object.__setattr__(self, '_field', field)
        object.__setattr__(self, '_owner', owner)

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, '_dc'), name)

    def __setattr__(self, name: str, value: Any) -> None:
        dc = object.__getattribute__(self, '_dc')
        for fld in dc_fields(dc):
            if fld.name == name:
                value = _castVal(fld.type, value)
                break
        setattr(dc, name, value)
        field: AutoDbField[Any] = object.__getattribute__(self, '_field')
        owner = object.__getattribute__(self, '_owner')
        field._saveToDb(owner, dc)

    def __str__(self) -> str:
        return str(object.__getattribute__(self, '_dc'))

    def __repr__(self) -> str:
        return repr(object.__getattribute__(self, '_dc'))


class AutoDbField(Generic[T]):
    def __init__(self, key: str, cast_type: type[T], default: T | None = None):
        self.key = key
        self.cast_type: Callable[..., Any] = cast_type  # type: type[T], but used as callable
        if default is None and is_dataclass(cast_type):
            self.default = cast_type()
        else:
            self.default = default
        self._cache_key = f'_cache_{key}'

    @overload
    def __get__(self, instance: None, owner: type) -> 'AutoDbField[T]': ...
    @overload
    def __get__(self, instance: object, owner: type) -> T: ...
    def __get__(self, instance: Any, owner: Any) -> Any:
        import db.sets as sets
        if instance is None: return self
        if hasattr(instance, self._cache_key):
            return getattr(instance, self._cache_key)
        val = sets.get(self.key, self.default)
        if self.cast_type and val is not None:
            try:
                if self.cast_type is bool:
                    val = val.lower() in ('true', '1', 'yes', 'on') if isinstance(val, str) else bool(val)
                elif self.cast_type is dict:
                    val = json.loads(val) if isinstance(val, str) and val else self.default
                elif is_dataclass(self.cast_type):
                    data = json.loads(val) if isinstance(val, str) else val
                    if isinstance(data, dict):
                        for fld in dc_fields(self.cast_type):
                            if fld.name in data:
                                data[fld.name] = _castVal(fld.type, data[fld.name])
                        dc = cast(Any, self.cast_type)(**data)
                    else:
                        dc = self.default
                    val = DcProxy(dc, cast(Any, self), instance)
                else:
                    val = self.cast_type(val)
            except (ValueError, TypeError, json.JSONDecodeError):
                lg.error(f'[AutoDbField] Failed to convert {val} to {self.cast_type}, use default[{self.default}]')
                val = self.default
        setattr(instance, self._cache_key, val)
        return val

    def __set__(self, instance, value):
        import db.sets as sets
        if self.cast_type and value is not None:
            try:
                if self.cast_type is bool:
                    value = _castVal(bool, value)
                elif self.cast_type is dict:
                    pass
                elif is_dataclass(self.cast_type) and is_dataclass(value):
                    _castDc(value)
                else:
                    value = cast(Callable[..., Any], self.cast_type)(value)
            except (ValueError, TypeError):
                lg.error(f'[AutoDbField] Failed to convert {value} to {self.cast_type} for key[{self.key}], use default[{self.default}]')
                value = self.default
        self._saveToDb(instance, value)
        setattr(instance, self._cache_key, value)

    def _saveToDb(self, instance, value):
        import db.sets as sets
        if self.cast_type is dict:
            sets.save(self.key, json.dumps(value, ensure_ascii=False))
        elif is_dataclass(value):
            sets.save(self.key, json.dumps(asdict(cast(Any, value)), ensure_ascii=False))
        else:
            sets.save(self.key, str(value))

@dataclass
class Muod:
  on:bool = False
  sz:int = 10

@dataclass
class Gpsk:
  eqDt:bool = False
  eqW:bool = False
  eqH:bool = False
  eqFsz:bool = False

@dataclass
class Ausl:
  on:bool = True
  skipLow:bool = True
  allLive:bool = False
  earlier:int = 2
  later:int = 0
  exRich:int = 1
  exPoor:int = 0
  ofsBig:int = 2
  ofsSml:int = 0
  dimBig:int = 2
  dimSml:int = 0
  namLon:int = 1
  namSht:int = 0
  typJpg:int = 0
  typPng:int = 0
  typHeic:int = 0
  fav:int = 0
  inAlb:int = 0
  usr:str = ''

@dataclass
class Mrg:
  on:bool = False
  albums:bool = False
  favs:bool = False
  tags:bool = False
  rating:bool = False
  desc:bool = False
  loc:bool = False
  vis:bool = False

@dataclass
class Excl:
  on:bool = True
  fndLes:int = 0
  fndOvr:int = 0
  filNam:str = ''

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
    gpsk = AutoDbField('gpsk', Gpsk )

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
