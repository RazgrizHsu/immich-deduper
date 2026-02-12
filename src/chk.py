import os
from dataclasses import dataclass, field

from conf import envs
from util import log

import db
import immich
import rtm

lg = log.get(__name__)

@dataclass
class ChkItem:
	key: str
	ok: bool
	msg: list[str] = field(default_factory=list)


def _parseVer(v: str):
	parts = v.split('.')
	return tuple(int(p) for p in parts if p.isdigit())

def ver() -> tuple[bool, list[str]]:
	try:
		import re
		verL = envs.version

		if envs.offline: return True, [verL, '(Offline - version check skipped)']

		url = "https://github.com/RazgrizHsu/immich-deduper/blob/main/pyproject.toml"

		try:
			txt = immich.getGithubRaw(url)
			mth = re.search(r'^version\s*=\s*"([^"]+)"', txt, re.MULTILINE)
			if not mth: return False, ['Version check failed', 'Cannot parse version from remote pyproject.toml']
			verR = mth.group(1)

			verLTuple = _parseVer(verL)
			verRTuple = _parseVer(verR)

			if verRTuple > verLTuple:
				return False, [
					f'New version available!',
					f'Local : {verL}',
					f'Remote: {verR}',
					f'Visit Github for update details'
				]
			else: return True, [verL]
		except RuntimeError as e: return False, ['Version check failed', str(e)]
	except Exception as e: return False, ['Version check failed', str(e)]

def testVec() -> tuple[bool, list[str]]:
	try:
		if not envs.qdrantUrl: return False, ['Qdrant URL not configured']

		db.vecs.init()

		import numpy as np

		if not db.vecs.conn: return False, ['Qdrant connection not initialized']

		tid = 999999999
		tvec = np.random.rand(2048).astype(np.float32)
		tvec = tvec / np.linalg.norm(tvec)

		try:
			db.vecs.save(tid, tvec, confirm=False)

			stored = db.vecs.getBy(tid)
			if not stored: return False, ['Vector retrieval failed after save']

			db.vecs.deleteBy([tid])
		except Exception as e:
			try: db.vecs.deleteBy([tid])
			except: pass

			errMsg = str(e)
			if "primitive" in errMsg: return False, ['Vector storage primitive error detected', errMsg]
			if "Vector" in errMsg: return False, ['Vector validation error', errMsg]
			return False, ['Vector operation failed', errMsg]

		return True, ['Vector write/read/delete test passed']
	except Exception as e: return False, ['Qdrant check failed', str(e)]

def psql() -> tuple[bool, list[str]]:
	try:
		if not all([envs.psqlHost, envs.psqlPort, envs.psqlDb, envs.psqlUser]): return False, ['PostgreSQL settings incomplete', 'Missing required connection parameters']

		if not db.psql.init(): return False, ['Cannot connect to PostgreSQL', 'Connection test failed']

		return True, ['PostgreSQL connection successful', f'Host: {envs.psqlHost}:{envs.psqlPort}']
	except Exception as e: return False, ['PostgreSQL check failed', str(e)]

def immichPath() -> tuple[bool, list[str]]:
	try:
		pth = rtm.immichPath
		if not pth: return False, ['IMMICH_PATH not configured']

		if not os.path.exists(pth): return False, ['IMMICH_PATH does not exist', f'Path: {pth}']

		if not os.path.isdir(pth): return False, ['IMMICH_PATH is not a directory', f'Path: {pth}']

		if not os.access(pth, os.R_OK): return False, ['IMMICH_PATH is not readable', f'Path: {pth}']

		rst = db.psql.testAssetsPath()
		if rst == "No Assets": return True, []

		if "OK" not in rst: return False, ['Asset path test failed', *rst]

		return True, []
	except Exception as e: return False, ['IMMICH_PATH check failed', str(e)]

def ddupData() -> tuple[bool, list[str]]:
	try:
		if not envs.ddupData: return False, ['DEDUP_DATA not configured']

		if not os.path.exists(envs.ddupData):
			try: os.makedirs(envs.ddupData, exist_ok=True)
			except Exception as e: return False, ['Cannot create DEDUP_DATA directory', f'Path: {envs.ddupData}', str(e)]

		if not os.path.isdir(envs.ddupData): return False, ['DEDUP_DATA is not a directory', f'Path: {envs.ddupData}']

		if not os.access(envs.ddupData, os.R_OK): return False, ['DEDUP_DATA is not readable', f'Path: {envs.ddupData}']

		if not os.access(envs.ddupData, os.W_OK): return False, ['DEDUP_DATA is not writable', f'Path: {envs.ddupData}']

		return True, ['DEDUP_DATA accessible', f'Path: {envs.ddupData}']
	except Exception as e: return False, ['DEDUP_DATA check failed', str(e)]

def immichLogic() -> tuple[bool, list[str]]:
	try:
		if envs.offline: return True, ['(Offline - logic check skipped)']

		checks = [
			(immich.checkLogicDelete(), "Delete logic"),
			(immich.checkLogicRestore(), "Restore logic"),
		]

		failed = [desc for ok, desc in checks if not ok]

		if failed:
			msgs = ["[system]"]
			for desc in failed: msgs.append(f"❌ {desc} check failed.")

			msgs += [
				"The Operation logic may have changed.",
				"Please **DO NOT use the system** and **check the GitHub repository** for updates immediately.",
				"If no updates are available, please report this issue to raz."
			]

			return False, msgs

		return True, ['Github checked!']
	except Exception as e: return False, ['Logic check error', str(e)]


def model() -> tuple[bool, list[str]]:
	try:
		from torchvision.models import ResNet152_Weights

		weights = ResNet152_Weights.DEFAULT
		url = weights.url
		filename = url.split('/')[-1]

		model_dir = os.path.join(envs.ddupData, 'models', 'checkpoints')
		local_path = os.path.join(model_dir, filename)

		if os.path.exists(local_path): return True, ['Model weights found locally', f'Path: {local_path}']

		if envs.offline:
			return False, [
				'Offline mode enabled but model weights not found',
				f'Please download to: {local_path}',
				f'Download URL: {url}'
			]

		try:
			import imgs
			imgs.getModel()
			return True, ['Model weights downloaded successfully']
		except Exception as e: return False, ['Failed to download model weights', str(e)]
	except Exception as e: return False, ['Model check failed', str(e)]


def exiftool() -> tuple[bool, list[str]]:
	try:
		from mod import bsh
		if not bsh.isInstalled(): return False, ['exiftool not found', 'Please install exiftool (e.g., apt install libimage-exiftool-perl)']

		import subprocess
		result = subprocess.run(['exiftool', '-ver'], capture_output=True, text=True)
		v = result.stdout.strip() if result.returncode == 0 else 'unknown'

		return True, [f'exiftool v{v}']
	except Exception as e: return False, ['exiftool check failed', str(e)]

def checkSystem() -> list[ChkItem]:
	return [
		ChkItem('ver', *ver()),
		ChkItem('data', *ddupData()),
		ChkItem('logic', *immichLogic()),
		ChkItem('vec', *testVec()),
		ChkItem('psql', *psql()),
		ChkItem('path', *immichPath()),
		ChkItem('model', *model()),
		ChkItem('exiftool', *exiftool()),
	]
