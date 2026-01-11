import os
from dataclasses import dataclass
from typing import List, Union

from conf import envs
from util import log

import db
import immich

lg = log.get(__name__)

@dataclass
class ChkInfo:
    ok: bool
    msg: Union[str, List[str]] = ''

@dataclass
class SysSte:
    ver: ChkInfo
    psql: ChkInfo
    path: ChkInfo
    data: ChkInfo
    vec: ChkInfo
    logic: ChkInfo


def _parseVer(v: str):
    parts = v.split('.')
    return tuple(int(p) for p in parts if p.isdigit())

def ver() -> ChkInfo:
    try:
        import re
        verL = envs.version

        url = "https://github.com/RazgrizHsu/immich-deduper/blob/main/pyproject.toml"

        try:
            txt = immich.getGithubRaw(url)
            mth = re.search(r'^version\s*=\s*"([^"]+)"', txt, re.MULTILINE)
            if not mth: return ChkInfo(False, ['Version check failed', 'Cannot parse version from remote pyproject.toml'])
            verR = mth.group(1)

            verLTuple = _parseVer(verL)
            verRTuple = _parseVer(verR)

            if verRTuple > verLTuple:
                return ChkInfo(False, [
                    f'New version available!',
                    f'Local : {verL}',
                    f'Remote: {verR}',
                    f'Visit Github for update details'
                ])
            else:
                return ChkInfo(True, [verL])

        except RuntimeError as e:
            return ChkInfo(False, ['Version check failed', str(e)])

    except Exception as e:
        return ChkInfo(False, ['Version check failed', str(e)])

def testVec() -> ChkInfo:
    try:
        if not envs.qdrantUrl: return ChkInfo(False, 'Qdrant URL not configured')

        db.vecs.init()

        import numpy as np

        if not db.vecs.conn: return ChkInfo(False, 'Qdrant connection not initialized')

        tid = 999999999
        tvec = np.random.rand(2048).astype(np.float32)
        tvec = tvec / np.linalg.norm(tvec)

        try:
            db.vecs.save(tid, tvec, confirm=False)

            stored = db.vecs.getBy(tid)
            if not stored: return ChkInfo(False, 'Vector retrieval failed after save')

            db.vecs.deleteBy([tid])

        except Exception as e:
            try:
                db.vecs.deleteBy([tid])
            except:
                pass

            errMsg = str(e)
            if "primitive" in errMsg: return ChkInfo(False, ['Vector storage primitive error detected', errMsg])
            if "Vector" in errMsg: return ChkInfo(False, ['Vector validation error', errMsg])
            return ChkInfo(False, ['Vector operation failed', errMsg])

        return ChkInfo(True, 'Vector write/read/delete test passed')

    except Exception as e:
        return ChkInfo(False, ['Qdrant check failed', str(e)])

def psql() -> ChkInfo:
    try:
        if not all([envs.psqlHost, envs.psqlPort, envs.psqlDb, envs.psqlUser]):
            return ChkInfo(False, ['PostgreSQL settings incomplete', 'Missing required connection parameters'])

        if not db.psql.init(): return ChkInfo(False, ['Cannot connect to PostgreSQL', 'Connection test failed'])

        return ChkInfo(True, ['PostgreSQL connection successful', f'Host: {envs.psqlHost}:{envs.psqlPort}'])
    except Exception as e:
        return ChkInfo(False, ['PostgreSQL check failed', str(e)])

def immichPath() -> ChkInfo:
    try:
        if not envs.immichPath: return ChkInfo(False, 'IMMICH_PATH not configured')

        if not os.path.exists(envs.immichPath): return ChkInfo(False, ['IMMICH_PATH does not exist', f'Path: {envs.immichPath}'])

        if not os.path.isdir(envs.immichPath): return ChkInfo(False, ['IMMICH_PATH is not a directory', f'Path: {envs.immichPath}'])

        if not os.access(envs.immichPath, os.R_OK): return ChkInfo(False, ['IMMICH_PATH is not readable', f'Path: {envs.immichPath}'])

        rst = db.psql.testAssetsPath()
        if rst == "No Assets": return ChkInfo(True)

        if "OK" not in rst:
            return ChkInfo(False, ['Asset path test failed', *rst])

        return ChkInfo(True)

    except Exception as e:
        return ChkInfo(False, ['IMMICH_PATH check failed', str(e)])

def mkitData() -> ChkInfo:
    try:
        if not envs.mkitData: return ChkInfo(False, 'DEDUP_DATA not configured')

        if not os.path.exists(envs.mkitData):
            try:
                os.makedirs(envs.mkitData, exist_ok=True)
            except Exception as e:
                return ChkInfo(False, ['Cannot create DEDUP_DATA directory', f'Path: {envs.mkitData}', str(e)])

        if not os.path.isdir(envs.mkitData): return ChkInfo(False, ['DEDUP_DATA is not a directory', f'Path: {envs.mkitData}'])

        if not os.access(envs.mkitData, os.R_OK): return ChkInfo(False, ['DEDUP_DATA is not readable', f'Path: {envs.mkitData}'])

        if not os.access(envs.mkitData, os.W_OK): return ChkInfo(False, ['DEDUP_DATA is not writable', f'Path: {envs.mkitData}'])

        return ChkInfo(True, ['DEDUP_DATA accessible', f'Path: {envs.mkitData}'])

    except Exception as e:
        return ChkInfo(False, ['DEDUP_DATA check failed', str(e)])

def immichLogic() -> ChkInfo:
    try:
        checks = [
            (immich.checkLogicDelete(), "Delete logic"),
            (immich.checkLogicRestore(), "Restore logic"),
        ]

        failed = [desc for ok, desc in checks if not ok]

        if failed:
            msgs = ["[system]"]
            for desc in failed:
                msgs.append(f"❌ {desc} check failed.")

            msgs += [
                "The Operation logic may have changed.",
                "Please **DO NOT use the system** and **check the GitHub repository** for updates immediately.",
                "If no updates are available, please report this issue to raz."
            ]

            return ChkInfo(False, msgs)

        return ChkInfo(True, 'Github checked!')

    except Exception as e:
        return ChkInfo(False, ['Logic check error', str(e)])



def checkSystem() -> SysSte:
    return SysSte(
        ver=ver(),
        psql=psql(),
        path=immichPath(),
        data=mkitData(),
        vec=testVec(),
        logic=immichLogic()
    )
