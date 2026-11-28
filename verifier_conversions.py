"""Régressions sur les conversions intermédiaires et les réserves alternatives."""
import json
from pathlib import Path
from analyse import analyze
from conversions import Conversions
from factions import payment_solver

d=json.loads(Path(__file__).with_name('coup61.json').read_text())
p=d['players']['1']
p.update(raceId=10,gold=2,ore=0,qic=0,knowledge=0,power=[0]*4,numAvailGaiaformers=1)
mine=(2,1,0,0,0,0,0)
assert payment_solver(p,True)(*mine)==('gaiaformeur vers Gaia pour 1 QIC','1 QIC → 1 minerai')
# Une véritable cible de mine accessible par l'entrée principale.
voisin=next(h for row in d['map'].values() for h in row.values()
            if h['planetType'] in range(1,8) and not h['buildings'])
voisin['planetType']=3
p['research'][2]=5
from analyse import distance
origine_mine=next(h for row in d['map'].values() for h in row.values()
                  if any(b['playerId']==1 and b['buildingId']>=4 for b in h['buildings']))
voisin['q'],voisin['r']=origine_mine['q']+1,origine_mine['r']
assert any('gaiaformeur vers Gaia' in prep for _,_,prep in analyze(d)['Mine ordinaire'])
assert not list(Conversions(p,True).paiements((2,1,0,0,0,0,1)))
p.update(raceId=1,qic=1,power=[0,0,0,3])
options=list(Conversions(p,False).paiements(mine))
assert len({fin for _,fin in options})==len(options)
assert any(fin.qic==0 and fin.bols.iii==3 for _,fin in options)
assert any(fin.qic==1 and fin.bols.iii==0 for _,fin in options)
# Hadsch Hallas : connaissance → crédits → QIC.
p.update(raceId=7,gold=0,knowledge=4,qic=0,power=[0]*4)
assert payment_solver(p,False)(0,0,0,1,0,0)
p.update(raceId=5,knowledge=0,race5brainstonePos=3)
assert payment_solver(p,False)(3,0,0,0,0,0)
# Une dépense groupée des Nevlas suffit à produire deux minerais.
p.update(raceId=13,race5brainstonePos=-1,power=[0,0,0,3])
assert payment_solver(p,False)(0,2,0,0,0,0)
p.update(raceId=3,ore=1,power=[0]*4)
assert payment_solver(p,True)(0,0,0,0,1,0)
assert payment_solver(p,False)(0,0,0,0,1,0) is None
# Vérifier les cinq choix supplémentaires sur le coup témoin.
temoin=json.loads(Path(__file__).with_name('coup61.json').read_text())
r=analyze(temoin)
assert len(r['Mine via le Crépuscule'])==17 and sum(map(len,r.values()))==83
print('Conversions en chaîne, paiements alternatifs et 83 choix du coup témoin vérifiés.')
