"""Tests de règles par faction sur des variantes construites du coup témoin."""
import json
from copy import deepcopy
from pathlib import Path
from analyse import analyze
from factions import HOME, payment_solver, structure_power, terraforming

sample=json.loads(Path(__file__).with_name('coup61.json').read_text())
def position(race):
    d=deepcopy(sample)
    p=d['players']['1']
    p.update(raceId=race,terraBoard=[1,2,3],activeTinkerTokenId=2,remainingTinkerTokens=[1,4,5],
             race5brainstonePos=3 if race==5 else -1)
    return d,p

def phase(d,name):
    d['gamestate']['name']=name
    return analyze(d)

for race in range(1,19):
    d,p=position(race)
    assert 'Passer' in analyze(d),race
    setup=phase(d,'stateSetupPlaceMine')['Placement initial']
    assert all(label.startswith('Institut' if race in (8,15) else 'Mine') for label,*_ in setup)
    assert terraforming(p,HOME[race])==0 if race<=14 else True

d,p=position(1);p['power'][0]=4
assert any('1 crédits, 1 minerais' in a for a,_,_ in phase(d,'stateGaiaRace1')['Phase Gaia'])
d,p=position(2)
assert any('connaissances' in a for a,_,_ in analyze(d)['Mine ordinaire'])
d,p=position(3);p.update(power=[0,0,0,0],ore=4,qic=0,knowledge=0)
assert payment_solver(p,True)(0,0,0,0,4,0) and payment_solver(p,False)(0,0,0,0,4,0) is None
d,p=position(4)
assert 'Exploration Gleens' in analyze(d)
p.update(power=[0,0,0,4],qic=0)
assert payment_solver(p,True)(0,0,0,1,0,0) is None
d,p=position(5);p['power']=[0,0,0,0]
assert payment_solver(p,True)(0,0,0,0,3,0)==()
d['gamestate']['args']=[2];p['score']=5
assert any('avant' in x for x,_,_ in phase(d,'stateChargePwr')['Charge passive'])
for race,group in [(6,'Institut Ambas'),(8,'Institut Ivits'),(11,'Institut Firaks'),
                   (12,'Bescods'),(15,'Bricolage'),(17,'Institut Moweyds')]:
    d,p=position(race)
    if race==11:
        mine=next(h for row in d['map'].values() for h in row.values()
                  if any(b['playerId']==1 and b['buildingId']==4 for b in h['buildings']))
        mine['buildings'][0]['buildingId']=6
    assert group in analyze(d),race
    p['hasUsedPiAction']=1
    assert group not in analyze(d),race

d,p=position(7);p.update(power=[0]*4,qic=0,ore=0,knowledge=0,gold=4)
assert payment_solver(p,True)(0,0,0,1,0,0)
d,p=position(9);assert any('3 connaissances' in row[0] for row in analyze(d)['Mine ordinaire'])
d,p=position(10);p.update(numAvailGaiaformers=1,qic=0,power=[0]*4)
assert payment_solver(p,True)(0,0,0,1,0,0)
d,p=position(12);assert structure_power(p,{'planetType':6},{'buildingId':9})==4
d,p=position(13);assert payment_solver(p,True)(0,0,0,0,4,0)==()
d,p=position(14);p['power'][0]=4
assert len(phase(d,'stateGaiaRace14')['Phase Gaia'])>1
d,p=position(15);assert terraforming(p,2)==3 and terraforming(p,4)==1
p['activeTinkerTokenId']=0
assert len(phase(d,'stateIncomeChoice')['Bricolage'])==1
d,p=position(16);assert terraforming(p,7)==1
d,p=position(17);assert structure_power(p,{'planetType':12},{'buildingId':4,'hasRing':1})==3
d,p=position(18);assert 'Exploration des Géants' in analyze(d)
d['board']['usedActions'][17]=1
assert 'Exploration des Géants' not in analyze(d)
print('18 factions, phases, pouvoirs et indisponibilités vérifiés sur positions construites.')
