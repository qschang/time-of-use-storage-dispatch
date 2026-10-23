import json,os,subprocess,sys
from pathlib import Path
import pytest
ENTRY=os.environ.get('STORAGE_ENTRY','/app/storage_dispatch.py')
if not Path(ENTRY).exists():
    ENTRY=str(Path(__file__).parents[1]/'solution/reference.py')
def case(): return {'battery':{'capacity_kWh':10.0,'initial_soc':0.5,'min_soc':0.2,'max_soc':0.9,'max_charge_kW':4.0,'max_discharge_kW':5.0,'charge_efficiency':0.9,'discharge_efficiency':0.9},'tariff':{'energy_rates':[1.0,3.0,0.5],'demand_rate':2.0},'steps':[{'duration_h':1.0,'load_kW':4.0,'solar_kW':0.0},{'duration_h':1.0,'load_kW':6.0,'solar_kW':0.0},{'duration_h':1.0,'load_kW':1.0,'solar_kW':3.0}]}
def run(tmp,d,existing=False):
 p=Path(tmp); i=p/'in.json'; o=p/'out.json'; i.write_text(json.dumps(d,separators=(',',':'))+'\n'); sentinel=b'keep\n';
 if existing:o.write_bytes(sentinel)
 r=subprocess.run([sys.executable,ENTRY,str(i),str(o)],capture_output=True,timeout=30)
 side={name:(p/name).exists() for name in ('report.json','journal.log','summary.json','ledger.json')}
 side['tmp']=bool(list(p.glob('.*.tmp')))
 return r,o,sentinel,side
@pytest.mark.core
def test_dispatch_schema_and_summary(tmp_path):
 """“输出是紧凑 UTF-8 JSON，末尾只有一个 LF，顶层键顺序为 `steps`、`summary`。”"""
 r,o,_,_=run(tmp_path,case()); assert r.returncode==0; assert list(json.loads(o.read_text()))==['steps','summary']; assert o.read_bytes().endswith(b'\n')
@pytest.mark.core
def test_discharge_respects_power_and_soc_bounds(tmp_path):
 """“充放电功率、SOC 上下界和效率均必须满足。”"""
 r,o,_,_=run(tmp_path,case()); x=json.loads(o.read_text()); assert all(0.2-1e-9<=s['soc_end']<=0.9+1e-9 for s in x['steps']); assert max(s['discharge_kW'] for s in x['steps'])<=5
@pytest.mark.core
def test_time_of_use_cost_and_demand_peak_are_separate(tmp_path):
 """“逐时能量费使用电网功率乘持续时间和该时段费率，需量费使用全账期电网功率峰值乘 `demand_rate`。”"""
 r,o,_,_=run(tmp_path,case()); x=json.loads(o.read_text()); assert x['summary']['demand_charge']==pytest.approx(x['summary']['peak_grid_kW']*2)
@pytest.mark.core
def test_solar_surplus_charges_battery(tmp_path):
 """“每个时段先计算净负荷 `load_kW - solar_kW`。”"""
 d=case(); d['steps']=[{'duration_h':1,'load_kW':1,'solar_kW':3}]; d['tariff']['energy_rates']=[1.0]; r,o,_,_=run(tmp_path,d); assert r.returncode==0 and json.loads(o.read_text())['steps'][0]['charge_kW']>0
@pytest.mark.recovery
def test_rerun_is_byte_identical(tmp_path):
 """“调度必须确定性，并在同一输入重跑时保持输出字节不变。”"""
 r,o,_,_=run(tmp_path,case()); before=o.read_bytes(); r,o,_,_=run(tmp_path,case()); assert r.returncode==0 and o.read_bytes()==before
@pytest.mark.boundary
def test_duplicate_key_is_rejected_without_output(tmp_path):
 """“任何输入校验、数值计算或发布失败都必须以非零状态拒收，并保持已有输出字节不变，不留下临时文件或部分结果。”"""
 p=Path(tmp_path); i=p/'in.json'; o=p/'out.json'; i.write_text('{"battery":{},"battery":{},"tariff":{},"steps":[]}'); r=subprocess.run([sys.executable,ENTRY,str(i),str(o)],capture_output=True)
 assert r.returncode!=0
 assert not o.exists()
 assert not list(p.glob('.*.tmp'))
 assert not (p/'report.json').exists()
 assert not (p/'journal.log').exists()
 assert not (p/'summary.json').exists()
@pytest.mark.boundary
def test_boolean_numeric_is_rejected(tmp_path):
 """“数值必须有限，SOC 位于 `[0,1]`。”"""
 d=case(); d['battery']['capacity_kWh']=True; r,o,_,side=run(tmp_path,d)
 assert r.returncode!=0
 assert not o.exists()
 assert not list(Path(tmp_path).glob('.*.tmp'))
 assert not (Path(tmp_path)/'report.json').exists()
 assert not (Path(tmp_path)/'journal.log').exists()
 assert not (Path(tmp_path)/'summary.json').exists()
@pytest.mark.boundary
def test_soc_order_is_rejected(tmp_path):
 """“SOC 位于 `[0,1]` 且满足 `min_soc <= initial_soc <= max_soc`。”"""
 d=case(); d['battery']['min_soc']=0.8; d['battery']['initial_soc']=0.5; r,o,_,side=run(tmp_path,d)
 assert r.returncode!=0
 assert not o.exists()
 assert not list(Path(tmp_path).glob('.*.tmp'))
 assert not (Path(tmp_path)/'report.json').exists()
 assert not (Path(tmp_path)/'journal.log').exists()
 assert not (Path(tmp_path)/'summary.json').exists()
@pytest.mark.boundary
def test_rate_length_must_match_steps(tmp_path):
 """“`tariff` 恰好包含与步骤数相同的非负 `energy_rates`。”"""
 d=case(); d['tariff']['energy_rates']=[1]; r,o,_,side=run(tmp_path,d)
 assert r.returncode!=0
 assert not o.exists()
 assert not list(Path(tmp_path).glob('.*.tmp'))
 assert not (Path(tmp_path)/'report.json').exists()
 assert not (Path(tmp_path)/'journal.log').exists()
 assert not (Path(tmp_path)/'summary.json').exists()
@pytest.mark.recovery
def test_existing_output_survives_rejection(tmp_path):
 """“保持已有输出字节不变，不留下临时文件或部分结果。”"""
 d=case(); d['steps'][0]['duration_h']=0; r,o,s,side=run(tmp_path,d,True)
 assert r.returncode!=0
 assert o.read_bytes()==s
 assert not list(Path(tmp_path).glob('.*.tmp'))
 assert not (Path(tmp_path)/'report.json').exists()
 assert not (Path(tmp_path)/'journal.log').exists()
 assert not (Path(tmp_path)/'summary.json').exists()
@pytest.mark.core
def test_total_cost_equals_components(tmp_path):
 """“摘要输出 `energy_cost`、`demand_charge`、`total_cost`。”"""
 r,o,_,_=run(tmp_path,case()); x=json.loads(o.read_text())['summary']; assert x['total_cost']==pytest.approx(x['energy_cost']+x['demand_charge'])
@pytest.mark.core
def test_no_simultaneous_charge_and_discharge(tmp_path):
 """“电池可以充电或放电，但不能同时进行；充放电功率、SOC 上下界和效率均必须满足。”"""
 r,o,_,_=run(tmp_path,case()); assert all(not (s['charge_kW']>0 and s['discharge_kW']>0) for s in json.loads(o.read_text())['steps'])

@pytest.mark.recovery
def test_missing_output_parent_is_rejected_without_creation(tmp_path):
 """“发布失败必须非零拒收，不能创建缺失的结果父目录或留下部分结果。”"""
 d=case(); i=Path(tmp_path)/'in.json'; i.write_text(json.dumps(d,separators=(',',':'))+'\n'); parent=Path(tmp_path)/'missing'; o=parent/'out.json'; r=subprocess.run([sys.executable,ENTRY,str(i),str(o)],capture_output=True); assert r.returncode!=0; assert not parent.exists(); assert not o.exists()

@pytest.mark.core
def test_low_price_precharge_reduces_later_demand_peak(tmp_path):
 """“调度需要统筹整个账期的能量费与需量费，不能只根据当前时段作局部决定。”"""
 d={'battery':{'capacity_kWh':10.0,'initial_soc':0.5,'min_soc':0.2,'max_soc':0.9,'max_charge_kW':2.0,'max_discharge_kW':2.0,'charge_efficiency':1.0,'discharge_efficiency':1.0},'tariff':{'energy_rates':[1.0,10.0,10.0],'demand_rate':20.0},'steps':[{'duration_h':1.0,'load_kW':1.0,'solar_kW':0.0},{'duration_h':1.0,'load_kW':5.0,'solar_kW':0.0},{'duration_h':1.0,'load_kW':5.0,'solar_kW':0.0}]}
 r,o,_,_=run(tmp_path,d); x=json.loads(o.read_text()); assert r.returncode==0; assert x['steps'][0]['charge_kW']==pytest.approx(2.0); assert x['summary']['peak_grid_kW']==pytest.approx(3.0)
