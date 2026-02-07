import inspect
import json
from dataclasses import dataclass, asdict, astuple
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Type, Tuple, TypeVar, Union, get_type_hints, get_origin, get_args, Protocol, Sequence

from util import log

lg = log.get(__name__)

T = TypeVar('T', bound='BaseDictModel')


class CursorProto(Protocol):
    @property
    def description(self) -> Optional[Sequence[Sequence[Any]]]: ...


# danger: replace dict to string method
orig_dict_toStr = dict.__str__

def custom_dict_str(self):
    items = [f"{k}:{v}" for k, v in self.items()]
    return "{" + ", ".join(items) + "}"




class Json(Dict[str, Any]):
    def __init__(self, data=None):
        super().__init__()
        if data:
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception as e:
                    raise ValueError(f"Error parsing JSON string: {e}")

            if isinstance(data, dict):
                for k, v in data.items():
                    if v == 'null':
                        self[k] = None
                    else:
                        self[k] = v


@dataclass
class BaseDictModel:
    _cheTHints = {}
    _cheTChks = {}

    _cheDbCols = {}
    _cheTCompx = {}

    def __str__(self):
        dic = self.toDict()


        strs = []
        for k, v, in dic.items():
            if isinstance(v, str): v = f"'{v}'"
            strs.append( f"{k}:{v}")

        return "{" + ", ".join(strs) + "}"

    @staticmethod
    def jsonSerializer(obj: Any) -> Any:
        if isinstance(obj, datetime): return obj.isoformat()
        if hasattr(obj, 'value'): return obj.value  # Handle Enum
        return str(obj)

    def toDict(self) -> Dict[str, Any]: return asdict(self)
    def toTuple(self) -> Tuple[Any, ...]: return astuple(self)
    def toJson(self) -> str: return json.dumps(self.toDict(), default=self.jsonSerializer, ensure_ascii=False)

    @classmethod
    def _getTypeHints(cls):
        if cls not in BaseDictModel._cheTHints:
            BaseDictModel._cheTHints[cls] = get_type_hints(cls)
        return BaseDictModel._cheTHints[cls]

    @classmethod
    def _isSubclass(cls, type_cls):
        ck = (cls, type_cls)
        if ck not in BaseDictModel._cheTChks:
            rst = inspect.isclass(type_cls) and issubclass(type_cls, BaseDictModel)
            BaseDictModel._cheTChks[ck] = rst
        return BaseDictModel._cheTChks[ck]


    @classmethod
    def _covBasicType(cls, val: Any, target_type: Type) -> Any:
        if target_type == str and not isinstance(val, str): return str(val)
        if target_type == int and not isinstance(val, int): return int(val)
        if target_type == float and not isinstance(val, float): return float(val)
        if target_type == bool and not isinstance(val, bool): return bool(val)
        return val

    @classmethod
    def _convert_model_from_dict(cls, val: Any, model_class: Type) -> Any:
        if isinstance(val, dict): return model_class.fromDic(val)
        return val

    @classmethod
    def _parse_json_to_model(cls, val: str, model_class: Type) -> Any:
        try:
            jso = json.loads(val)
            if isinstance(jso, dict): return model_class.fromDic(jso)
        except:
            pass
        return val

    @classmethod
    def _mkWithFallback(cls, processed_data: Dict[str, Any],
                                      original_data: Dict[str, Any],
                                      type_hints: Dict[str, Type]) -> Any:
        try:
            return cls(**processed_data)
        except (TypeError, ValueError) as e:
            filtered_data = {k: v for k, v in original_data.items() if k in type_hints}
            try:
                return cls(**filtered_data)
            except:
                raise e

    @classmethod
    def _procTypedField(cls, key: str, val: Any, typ: Type) -> Any:
        origin = get_origin(typ)

        if val is None:
            if origin is list:
                return []
            return None

        if origin is None:
            if cls._isSubclass(typ):
                rst = cls._convert_model_from_dict(val, typ)
                if rst != val: return rst
                if isinstance(val, str): return cls._parse_json_to_model(val, typ)
            elif inspect.isclass(typ) and issubclass(typ, Enum):
                if isinstance(val, str):
                    for member in typ:
                        if member.value == val: return member
                    return val
            else:
                try:
                    return cls._covBasicType(val, typ)
                except (ValueError, TypeError):
                    pass
            return val

        if origin is list:
            if isinstance(val, list):
                ctyp = get_args(typ)[0]
                if cls._isSubclass(ctyp):
                    return [ctyp.fromDic(item) for item in val]
                else:
                    coved = []
                    for item in val:
                        try:
                            coved.append(cls._covBasicType(item, ctyp))
                        except (ValueError, TypeError):
                            coved.append(item)
                    return coved
            elif isinstance(val, str):
                try:
                    lst = json.loads(val)
                    if isinstance(lst, list):
                        ctyp = get_args(typ)[0]
                        if cls._isSubclass(ctyp):
                            return [ctyp.fromDic(item) for item in lst]
                        else:
                            coved = []
                            for item in lst:
                                try:
                                    coved.append(cls._covBasicType(item, ctyp))
                                except (ValueError, TypeError):
                                    coved.append(item)
                            return coved
                except:
                    pass
            return val

        if origin is dict: return val

        if origin is Union:
            targs = get_args(typ)
            rtyps = [t for t in targs if t is not type(None)]

            if len(rtyps) == 1:
                real_type = rtyps[0]
                if cls._isSubclass(real_type):
                    rst = cls._convert_model_from_dict(val, real_type)
                    if rst != val: return rst
                    if isinstance(val, str): return cls._parse_json_to_model(val, real_type)
                else:
                    try:
                        return cls._covBasicType(val, real_type)
                    except (ValueError, TypeError):
                        pass
            return val

        return val

    @classmethod
    def _procJsonFields(cls, data: Dict[str, Any], type_hints: Dict[str, Type]) -> Dict[str, Any]:
        for fname, ftype in type_hints.items():
            if ftype == Json and fname in data and isinstance(data[fname], str):
                try:
                    data[fname] = Json(data[fname])
                except Exception as e:
                    raise ValueError(f"Error parsing JSON for {fname}: {str(e)}")
        return data

    @classmethod
    def _hasCompx(cls, type_hints):
        if cls not in cls._cheTCompx:
            fdCompx = set()
            for key, hint_type in type_hints.items():
                origin = get_origin(hint_type)
                if origin is list or origin is Union:
                    fdCompx.add(key)
                    continue

                if origin is None:
                    if cls._isSubclass(hint_type):
                        fdCompx.add(key)
                        continue
                    if inspect.isclass(hint_type) and issubclass(hint_type, Enum):
                        fdCompx.add(key)
                        continue

            cls._cheTCompx[cls] = fdCompx

        return cls._cheTCompx[cls]

    @classmethod
    def fromStr(cls: Type[T], src: str) -> T:
        try:
            data = json.loads(src)
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict after JSON parse, got {type(data).__name__}")
            result = cls.fromDic(data)
            if result is None:
                raise ValueError(f"Failed to create {cls.__name__} from data")
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")

    @classmethod
    def fromJS(cls: Type[T], dic:Dict[str,Any]) -> T:
        if not dic: return cls()

        data = dic.get('data')
        if not data: return cls()

        try:
            obj = json.loads(data)
            return cls.fromDic(obj)

        except Exception as e:
            raise ValueError(f"Invalid data from JS, {e}, data[{data}]")

    @classmethod
    def fromDic(cls: Type[T], src: Dict[str, Any]) -> T:
        try:
            if not src: return cls()

            typs = cls._getTypeHints()

            done = {}
            for key, val in src.items():
                if key not in typs: continue

                hint_type = typs[key]
                done[key] = cls._procTypedField(key, val, hint_type)

            return cls._mkWithFallback(done, src, typs)
        except Exception as e:
            lg.exception(e)
            raise RuntimeError(f"Error converting dict to {cls.__name__}: {e}, src={src}")


    @classmethod
    def fromDB(cls: Type[T], cursor: CursorProto, row: tuple) -> T:
        try:
            if not row: raise ValueError(f"row is empty")

            if cursor.description is None:
                raise TypeError("cursor.description is None")
            ck = tuple(desc[0] for desc in cursor.description)
            cols = cls._cheDbCols.get(ck)
            if cols is None:
                cols = list(ck)
                cls._cheDbCols[ck] = cols

            data = dict(zip(cols, row))
            typs = cls._getTypeHints()

            jfds = [fname for fname, ftype in typs.items()
                           if ftype == Json and fname in data and isinstance(data[fname], str)]

            if jfds: data = cls._procJsonFields(data, typs)

            fdCompx = cls._hasCompx(typs)

            done = {}
            for key, val in data.items():
                if key not in typs: continue

                typ = typs[key]
                origin = get_origin(typ)

                if (key in fdCompx
                    or
                    (
                        isinstance(val, str) and cls._isSubclass(typ)
                        or
                        (origin is Union and any(cls._isSubclass(t) for t in get_args(typ) if t is not type(None)))
                    )
                ):
                    done[key] = cls._procTypedField(key, val, typs[key])
                else:
                    done[key] = val

            return cls._mkWithFallback(done, data, typs)
        except Exception as e:
            lg.error(f"Error converting DB row to {cls.__name__}: {e}, row={row}")
            raise e
