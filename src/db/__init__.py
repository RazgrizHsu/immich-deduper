from conf import ks, Optional
from util import log

lg = log.get(__name__)

import db.pics as pics
import db.sets as sets
import db.vecs as vecs
import db.psql as psql
import db.sim as sim


def init():
    try:
        sets.init()
        pics.init()
        vecs.init()
        psql.init()
        lg.info('All databases initialized successfully')
    except Exception as e:
        raise RuntimeError(f'Database initialization failed: {str(e)}')

def close():
    try:
        sets.close()
        vecs.close()
        lg.info('All database connections closed successfully')
    except Exception as e:
        lg.error(f'Failed to close database connections: {str(e)}')
        return False

    return True

def resetAllData():
    try:
        pics.clearAll()
        vecs.cleanAll()
        lg.info('[clear] All records cleared successfully')
    except Exception as e:
        lg.error(f'[clear] Failed to clear all records: {str(e)}')
        return False

    return True


class AutoDbField:
    def __init__(self, key, cast_type=None, default=None):
        self.key = key
        self.cast_type = cast_type
        self.default = default
        self._cache_key = f'_cache_{key}'

    def __get__(self, instance, owner):
        if instance is None: return self
        if hasattr(instance, self._cache_key):
            return getattr(instance, self._cache_key)
        val = sets.get(self.key, self.default)
        if self.cast_type and val is not None:
            try:
                if self.cast_type is bool:
                    val = val.lower() in ('true', '1', 'yes', 'on') if isinstance(val, str) else bool(val)
                else:
                    val = self.cast_type(val)
            except (ValueError, TypeError):
                lg.error(f'[AutoDbField] Failed to convert {val} to {self.cast_type}, use default[{self.default}]')
                val = self.default
        setattr(instance, self._cache_key, val)
        return val

    def __set__(self, instance, value):
        if self.cast_type and value is not None:
            try:
                if self.cast_type is bool:
                    value = value.lower() in ('true', '1', 'yes', 'on') if isinstance(value, str) else bool(value)
                else:
                    value = self.cast_type(value)
            except (ValueError, TypeError):
                lg.error(f'[AutoDbField] Failed to convert {value} to {self.cast_type} for key[{self.key}], use default[{self.default}]')
                value = self.default
        sets.save(self.key, str(value))
        setattr(instance, self._cache_key, value)


class DtoSets:
    tskFloat:bool = AutoDbField('tskFloat', bool, False) #type:ignore

    usrId:Optional[str] = AutoDbField('usrId', str, '') #type:ignore

    photoQ:str = AutoDbField('photoQ', str, ks.db.thumbnail) #type:ignore
    thMin:float = AutoDbField('simMin', float, 0.93) #type:ignore

    autoNext:bool = AutoDbField('autoNext', bool, True) #type:ignore
    showGridInfo:bool = AutoDbField('showGridInfo', bool, True) #type:ignore

    rtree:bool = AutoDbField('simRtree', bool, False) #type:ignore
    rtreeMax:int = AutoDbField('simMaxItems', int, 200) #type:ignore

    muod:bool = AutoDbField('muod', bool, False) #type:ignore
    muod_Size:int = AutoDbField('muod_Size', int, 10) #type:ignore
    muod_EqDt:bool = AutoDbField('muod_EqDt', bool, False) #type:ignore
    muod_EqW:bool = AutoDbField('muod_EqW', bool, False) #type:ignore
    muod_EqH:bool = AutoDbField('muod_EqH', bool, False) #type:ignore
    muod_EqFs:bool = AutoDbField('muod_EqFs', bool, False) #type:ignore

    ausl:bool = AutoDbField('ausl', bool, True ) #type:ignore
    ausl_SkipLow:bool = AutoDbField('ausl_SkpLow', bool, True ) #type:ignore
    ausl_AllLive:bool = AutoDbField('ausl_AllLive', bool, False ) #type:ignore

    ausl_Earlier:int = AutoDbField('ausl_Earlier', int, 2 ) #type:ignore
    ausl_Later:int = AutoDbField('ausl_Later', int, 0 ) #type:ignore
    ausl_ExRich:int = AutoDbField('ausl_ExRich', int, 1 ) #type:ignore
    ausl_ExPoor:int = AutoDbField('ausl_ExPoor', int, 0 ) #type:ignore
    ausl_OfsBig:int = AutoDbField('ausl_OfsBig', int, 2 ) #type:ignore
    ausl_OfsSml:int = AutoDbField('ausl_OfsSml', int, 0 ) #type:ignore
    ausl_DimBig:int = AutoDbField('ausl_DimBig', int, 2 ) #type:ignore
    ausl_DimSml:int = AutoDbField('ausl_DimSml', int, 0 ) #type:ignore
    ausl_NamLon:int = AutoDbField('ausl_NmLon', int, 1 ) #type:ignore
    ausl_NamSht:int = AutoDbField('ausl_NmSht', int, 0 ) #type:ignore
    ausl_TypJpg:int = AutoDbField('ausl_TypJpg', int, 0 ) #type:ignore
    ausl_TypPng:int = AutoDbField('ausl_TypPng', int, 0 ) #type:ignore
    ausl_TypHeic:int = AutoDbField('ausl_TypHeic', int, 0 ) #type:ignore
    ausl_Fav:int = AutoDbField('ausl_Fav', int, 0 ) #type:ignore
    ausl_InAlb:int = AutoDbField('ausl_InAlb', int, 0 ) #type:ignore
    asul_Usr:str = AutoDbField('asul_Usr', str, '' ) #type:ignore

    excl:bool = AutoDbField('excl', bool, True ) #type:ignore
    excl_FndLes:int = AutoDbField('excl_FndLes', int, 0) #type:ignore
    excl_FilNam:str = AutoDbField('excl_FilNam', str, '') #type:ignore

    gpuAutoMode:bool = AutoDbField('gpuAutoMode', bool, True) #type:ignore
    gpuBatchSize:int = AutoDbField('gpuBatchSize', int, 8) #type:ignore

    cpuAutoMode:bool = AutoDbField('cpuAutoMode', bool, True) #type:ignore
    cpuWorkers:int = AutoDbField('cpuWorkers', int, 4) #type:ignore

    def checkIsExclude(self, asset) -> bool:
        if not self.excl or not self.excl_FilNam:
            return False

        if not asset or not asset.originalFileName:
            return False

        filters = [f.strip() for f in self.excl_FilNam.split(',') if f.strip()]
        if not filters:
            return False

        fileName = asset.originalFileName.lower()

        for flt in filters:
            flt = flt.lower()
            if flt.startswith('.'):
                if fileName.endswith(flt): return True
            elif flt in fileName: return True

        return False

    @classmethod
    def get(cls, key, default=None):
        value = sets.get(key, default)
        return value

    @classmethod
    def save(cls, key, value):
        return sets.save(key, str(value))


    def clearCache(self):
        for attr_name in dir(self.__class__):
            attr = getattr(self.__class__, attr_name)
            if isinstance(attr, AutoDbField):
                cache_key = attr._cache_key
                if hasattr(self, cache_key): delattr(self, cache_key)

# global
dto = DtoSets()
