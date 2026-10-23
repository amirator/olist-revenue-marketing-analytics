"""One command: python run.py  (download -> SQL build -> KPIs/Power BI exports -> scorecard -> README -> tests)"""
import subprocess, sys
from src import download, build, dashboard, readme
download.main()
con = build.build(); build.export_kpis(con); build.export_powerbi(con); con.close()
dashboard.main(); readme.main()
sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q"]))
