import argparse,json,xml.etree.ElementTree as ET
def main():
 p=argparse.ArgumentParser(); p.add_argument('--junit',required=True); p.add_argument('--report-out',required=True); p.add_argument('--reward-out',required=True); p.add_argument('--config',required=False); a=p.parse_args(); root=ET.parse(a.junit).getroot(); suite=root.find('testsuite') or root; total=int(suite.attrib.get('tests',0)); bad=sum(int(suite.attrib.get(k,0)) for k in ('failures','errors','skipped')); reward=1.0 if total==12 and bad==0 else 0.0; json.dump({'schema_version':1,'tests':total,'bad':bad,'reward':reward},open(a.report_out,'w',encoding='utf-8'),ensure_ascii=False,indent=2); open(a.reward_out,'w').write(f'{reward:.3f}\n')
if __name__=='__main__': main()
