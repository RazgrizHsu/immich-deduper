import shutil
import subprocess
import json
from typing import Dict, List, Optional, Any
from util import log

lg = log.get(__name__)

def isInstalled() -> bool: return shutil.which('exiftool') is not None

def read(path: str) -> Optional[Dict[str, Any]]:
	try:
		result = subprocess.run(['exiftool', '-json', path], capture_output=True, text=True)
		if result.returncode != 0:
			lg.error(f"[exif] read failed: {path} - {result.stderr}")
			return None
		data = json.loads(result.stdout)
		return data[0] if data else None
	except Exception as e:
		lg.error(f"[exif] read failed: {path} - {e}")
		return None

def write(path: str, tags: Dict[str, Any]) -> bool:
	args = ['exiftool', '-overwrite_original']
	for k, v in tags.items():
		if v is None: continue
		if isinstance(v, list):
			for item in v: args.append(f'-{k}={item}')
		else: args.append(f'-{k}={v}')
	args.append(path)

	result = subprocess.run(args, capture_output=True, text=True)
	if result.returncode != 0:
		lg.error(f"[exif] write failed: {path}")
		lg.error(f"[exif] stdout: {result.stdout}")
		lg.error(f"[exif] stderr: {result.stderr}")
		return False
	return True

def writeBatch(items: List[tuple]) -> List[bool]:
	results = []
	for path, tags in items: results.append(write(path, tags))
	return results
