"""Régressions sur le coup témoin. Lancer python verifier.py."""
from pathlib import Path
import json
from analyse import analyze, distance

d = json.loads(Path(__file__).with_name('coup61.json').read_text())
r = analyze(d)
assert len(r['Laboratoire']) == 24
assert len(r['Recherche']) == 6
assert all(row[2] == 'direct' for row in r['Artefact'])
assert any(row[0].startswith('Glace (2, -1)') and row[2]=='direct' for row in r['Mine via le Crépuscule'])
assert all('Glace' not in row[0] and 'Gaia' not in row[0] for group in r if 'étape' in group for row in r[group])
assert all(not row[0].startswith('Gagner 2 minerais') for row in r['Puissance'])
d['board']['usedActions'][37] = int(d['gamestate']['active_player'])
assert 'Mine via le Crépuscule' not in analyze(d)
print('Contrôles du coup témoin réussis.')

from copy import deepcopy
from objectifs import technologies, synthese, bonus_manche, classement, EFFETS, gains_technologie

case=deepcopy(d)
pid=case['gamestate']['active_player']
p=case['players'][pid]
board=case['board']
advanced=board['advTechs'][6]

def choices():
    return [(cover,tracks) for tile,cover,tracks in technologies(case,pid)[0] if tile==advanced]

assert not choices()
p['techs']=[{'techId':1,'isCovered':0,'isActionUsed':0}]
p['fedTiles']=[{'isGreen':1}]
for ship in board['lostFleet']['ships'][1:3]:
    ship['playerIds'].append(int(pid))
assert choices()
p['research'][1]=4
assert 1 not in choices()[0][1]
p['fedTiles'].append({'isGreen':1})
assert 1 in choices()[0][1]
other=next(v for k,v in case['players'].items() if k!=pid)
other['research'][1]=5
assert 1 not in choices()[0][1]
board['lostFleet']['scoreBoard']=0
p['score']=24
assert not choices()
p['score']=25
assert choices()
p['techs'][0]['isCovered']=1
assert not choices()
p['techs'][0]['isCovered']=0
for token in p['fedTiles']: token['isGreen']=0
assert not choices()
p['fedTiles'][0]['isGreen']=1
assert any('recouvrir 1' in label for label,_,_ in analyze(case)['Laboratoire'])
board['advTechs'][6]=0
assert not choices()
assert bonus_manche(board,{'comptoir':1})==4
assert classement({'a':4,'b':4,'c':2})=={'a':15,'b':15,'c':6}
assert len(synthese(case)['manches'])==6
assert gains_technologie(33,'passage',{'astéroïdes':3})=={'PV':6}
assert gains_technologie(31,'acquisition',{'secteurs lointains':2})=={'PV':8}
print('Objectifs, technologies et conditions de la Flotte perdue vérifiés.')
from objectifs import prendre_avancee
board['advTechs'][6]=advanced
result=prendre_avancee(case,pid,advanced,1,2,[0])
assert result['board']['advTechs'][6]==0 and board['advTechs'][6]==advanced
after=result['players'][pid]
assert after['techs'][0]['isCovered'] and not after['fedTiles'][0]['isGreen']
assert after['research'][2]==p['research'][2]+1
assert advanced not in [tile for tile,_,_ in technologies(result,pid)[0]]
