from pathlib import Path
H=Path(__file__).resolve().parent;W=H.parent
s=(W/'world-package-real-api-037-001/run_measured.py').read_text(encoding='utf-8')
s=s.replace("SRC=W/'world-package-api-candidate-037'","SRC=W/'world-package-039'")
s=s.replace('layout-40b38c14f718490a13b88a87','layout-174d4bddd3f8efcf689c7e40')
s=s.replace('67a54c4362c46b64d27a5d362defef878796b357adfb092d1827b3d25832a301','ef58d7b81e37182f86dd22defea9294ccfa4b1696fb7bb3810ca80069b85fe0a')
s=s.replace('MEASURED_REAL037','MEASURED_REAL039').replace("'installed':False","'installed':True")
p=H/'run_measured.py';assert not p.exists();p.write_text(s,encoding='utf-8')
