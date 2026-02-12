from dataclasses import dataclass, field, is_dataclass, asdict, fields as dc_fields, MISSING

@dataclass
class PairKv:
	k:str = ''
	v:int = 0

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
	usr:PairKv = field(default_factory=PairKv)
	pth:PairKv = field(default_factory=PairKv)

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
