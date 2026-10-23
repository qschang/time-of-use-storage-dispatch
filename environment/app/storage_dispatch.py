import json,sys,math,os
from pathlib import Path

def finite(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def fail(code): sys.stderr.write('运行拒收: '+code+'\n'); raise SystemExit(1)
def main():
    if len(sys.argv)!=3: fail('BAD_INPUT')
    ip,op=map(Path,sys.argv[1:])
    try:
        d=json.loads(ip.read_text(encoding='utf-8'),object_pairs_hook=lambda p: (_ for _ in ()).throw(ValueError()) if len({k for k,v in p})!=len(p) else dict(p))
        b,t,steps=d['battery'],d['tariff'],d['steps']
        if set(d)!={'battery','tariff','steps'} or not isinstance(b,dict) or not isinstance(t,dict) or not isinstance(steps,list) or not 1<=len(steps)<=96: fail('BAD_INPUT')
        for k in ['capacity_kWh','initial_soc','min_soc','max_soc','max_charge_kW','max_discharge_kW','charge_efficiency','discharge_efficiency']:
            if k not in b or not finite(b[k]): fail('BAD_INPUT')
        if not (b['capacity_kWh']>0 and 0<=b['min_soc']<=b['initial_soc']<=b['max_soc']<=1 and b['max_charge_kW']>=0 and b['max_discharge_kW']>=0 and 0<b['charge_efficiency']<=1 and 0<b['discharge_efficiency']<=1): fail('BAD_INPUT')
        rates=t['energy_rates'];
        if set(t)!={'energy_rates','demand_rate'} or not isinstance(rates,list) or len(rates)!=len(steps) or not finite(t['demand_rate']) or t['demand_rate']<0 or any(not finite(x) or x<0 for x in rates): fail('BAD_INPUT')
        for s in steps:
            if set(s)!={'duration_h','load_kW','solar_kW'} or any(not finite(s[k]) for k in s) or s['duration_h']<=0 or s['load_kW']<0 or s['solar_kW']<0: fail('BAD_INPUT')
        soc=b['initial_soc']; rows=[]; energy=0.0; peak=0.0
        for i,s in enumerate(steps):
            net=s['load_kW']-s['solar_kW']; dt=s['duration_h']; discharge=min(max(0.0,net),b['max_discharge_kW'],max(0.0,(soc-b['min_soc'])*b['capacity_kWh']*b['discharge_efficiency']/dt)); charge=min(max(0.0,-net),b['max_charge_kW'],max(0.0,(b['max_soc']-soc)*b['capacity_kWh']/(b['charge_efficiency']*dt))); grid=net-discharge+charge; soc+=(charge*b['charge_efficiency']-discharge/b['discharge_efficiency'])*dt/b['capacity_kWh']; cost=grid*dt*rates[i]; energy+=cost; peak=max(peak,grid); rows.append({'index':i,'grid_kW':round(grid,10),'charge_kW':round(charge,10),'discharge_kW':round(discharge,10),'soc_end':round(soc,10),'energy_cost':round(cost,10)})
        out={'steps':rows,'summary':{'energy_cost':round(energy,10),'demand_charge':round(peak*t['demand_rate'],10),'total_cost':round(energy+peak*t['demand_rate'],10),'peak_grid_kW':round(peak,10),'final_soc':round(soc,10)}}; payload=json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n'; op.parent.mkdir(parents=True,exist_ok=True); tmp=op.with_name('.'+op.name+'.tmp'); tmp.write_text(payload,encoding='utf-8'); os.replace(tmp,op)
    except SystemExit: raise
    except Exception: fail('BAD_INPUT')
if __name__=='__main__': main()
