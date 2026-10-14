import json,sys,os,platform,shutil,importlib.metadata
from pathlib import Path
c=Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
print(json.dumps({"host":platform.node(),"user":os.environ.get("USERNAME"),"python":sys.version,"executable":sys.executable,"playwright":importlib.metadata.version("playwright"),"chrome":str(c),"chrome_exists":c.is_file(),"free_C":shutil.disk_usage("C:\\").free,"free_D":shutil.disk_usage("D:\\").free}))
