import os
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple, Union

from dsh import htm
from conf import ks, envs, co
from util import log
from .base import BaseDictModel

lg = log.get(__name__)






@dataclass
class SimInfo(BaseDictModel):
    aid: int = 0
    score: float = 0
    isSelf: bool = False


@dataclass
class Usr(BaseDictModel):
    id: str = ''
    name: str = ''
    email: str = ''


@dataclass
class AssetExif(BaseDictModel):
    make: Optional[str] = None
    model: Optional[str] = None
    exifImageWidth: Optional[int] = None
    exifImageHeight: Optional[int] = None
    fileSizeInByte: Optional[int] = None
    orientation: Optional[str] = None
    dateTimeOriginal: Optional[str] = None
    modifyDate: Optional[str] = None
    lensModel: Optional[str] = None
    fNumber: Optional[float] = None
    focalLength: Optional[float] = None
    iso: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    fps: Optional[float] = None
    exposureTime: Optional[str] = None
    livePhotoCID: Optional[str] = None
    timeZone: Optional[str] = None
    projectionType: Optional[str] = None
    profileDescription: Optional[str] = None
    colorspace: Optional[str] = None
    bitsPerSample: Optional[int] = None
    autoStackId: Optional[str] = None
    rating: Optional[int] = None
    updatedAt: Optional[str] = None
    updateId: Optional[str] = None

    def toAvDict(self):
        return {k: v for k, v in self.toDict().items() if v is not None}


@dataclass
class AssetViewOnly(BaseDictModel):

    isMain:bool = False

    cntRelats: int = 0

    score: float = 0.0

    srcAutoId: int = 0
    isRelats: bool = False

    muodId: int = 0

@dataclass
class Album(BaseDictModel):
    id: str = ""
    ownerId: str = ""
    albumName: str = ""
    description: str = ""
    updatedAt: Optional[str] = None
    albumThumbnailAssetId: Optional[str] = None
    isActivityEnabled: bool = True
    order: str = "desc"

@dataclass
class AssetFace(BaseDictModel):
    id: str = "" #asset_faces.id
    personId: str = ""
    name: str = "" # person.name
    ownerId: str = "" #person.ownerId
    imageWidth: int = 0
    imageHeight: int = 0
    boundingBoxX1: int = 0
    boundingBoxY1: int = 0
    boundingBoxX2: int = 0
    boundingBoxY2: int = 0
    sourceType: str = ""
    deletedAt: str = ""

@dataclass
class Tags(BaseDictModel):
    id: str = ""
    value: str = ""
    userId: str = ""

@dataclass
class AssetExInfo(BaseDictModel):
    albs: List[Album] = field(default_factory=list)
    facs: List[AssetFace] = field(default_factory=list)
    tags: List[Tags] = field(default_factory=list)


@dataclass
class Asset(BaseDictModel):
    autoId: int = 0
    id: str = ""
    ownerId: str = ""
    deviceId: Optional[str] = None
    vdoId: Optional[str] = None
    type: Optional[str] = None
    originalFileName: str = ""
    originalPath: str = ""
    fileCreatedAt: Optional[str] = None
    fileModifiedAt: Optional[str] = None
    isFavorite: int = 0
    isArchived: int = 0
    localDateTime: Optional[str] = None
    pathThumbnail: Optional[str] = None
    pathPreview: Optional[str] = None
    pathVdo: Optional[str] = None
    jsonExif: AssetExif = field(default_factory=AssetExif)
    isVectored: Optional[int] = 0
    simOk: Optional[int] = 0
    simInfos: List[SimInfo] = field(default_factory=list)
    simGIDs: List[int] = field(default_factory=list)


    # dynamic fill
    ex: Optional[AssetExInfo] = None
    vw: AssetViewOnly = field(default_factory=AssetViewOnly)

    def getImagePath(self, photoQ=None):
        path = envs.pth.forImg(self.pathThumbnail, self.pathPreview, photoQ)
        if not path: raise RuntimeError(f"the thumbnail path is empty, assetId[{self.id}]")
        return path

