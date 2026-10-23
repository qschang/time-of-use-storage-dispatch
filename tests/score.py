import argparse,json,os,xml.etree.ElementTree as ET
def main():
 p=argparse.ArgumentParser(); p.add_argument('--junit',required=True); p.add_argument('--report-out',required=True); p.add_argument('--reward-out',required=True); p.add_argument('--config',required=True); a=p.parse_args()
 cfg=json.load(open(a.config,encoding='utf-8')); gate=set(cfg.get('gate_tests',[])); scored=cfg.get('tests',{}); expected=gate|set(scored)
 root=ET.parse(a.junit).getroot(); suite=root.find('testsuite') or root; cases={x.attrib.get('classname','')+'::'+x.attrib.get('name',''):x for x in suite.findall('.//testcase')}
 bad=[]
 for node in expected:
  c=cases.get(node)
  if c is None or c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None: bad.append(node)
 extra=set(cases)-expected
 valid=(len(cases)==len(expected) and not extra and not bad)
 reward=1.0 if valid else 0.0
 report={'schema_version':1,'expected':sorted(expected),'observed':sorted(cases),'missing':sorted(expected-set(cases)),'extra':sorted(extra),'bad':sorted(bad),'reward':reward}
 json.dump(report,open(a.report_out,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
 try: os.chmod(a.reward_out,0o644)
 except OSError: pass
 open(a.reward_out,'w').write(f'{reward:.3f}\n')
if __name__=='__main__': main()
