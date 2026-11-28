"""Vérifier les transitions de puissance et leurs branchements dans le générateur."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path

from analyse import analyze
from puissance import Bols, charge_recherche, reactions, revenus

for i, ii, iii, pierre, demande in product(range(4), range(4), range(3), range(-1,4), range(12)):
    avant = Bols(2,i,ii,iii,pierre)
    for priorite in (False, True):
        apres, charge = avant.charger(demande, priorite)
        assert charge == min(demande, 2*i+ii+{1:2,2:1}.get(pierre,0))
        assert apres.gaia==2 and apres.i+apres.ii+apres.iii==i+ii+iii
        assert apres.ii+2*apres.iii + max(0, apres.pierre-1) == ii+2*iii+max(0,pierre-1)+charge
assert Bols(0,2,1,0).charger(3)[0]==Bols(0,0,2,1)
assert len(revenus(Bols(0,0,1,0),[1],[1]))==2
assert revenus(Bols(0,0,0,0),[],[],2)==[Bols(0,0,0,2)]

sample=json.loads(Path(__file__).with_name('coup61.json').read_text())
d=deepcopy(sample)
p=d['players']['1']
p.update(power=[0,2,1,0],score=1)
options=list(reactions(p,5))
assert options[1][1:]==(Bols(0,0,3,0),1)
assert p['power']==[0,2,1,0]
p.update(raceId=5,race5brainstonePos=2,power=[0,0,1,0],score=9)
assert len({s for _,s,_ in reactions(p,1)})>=3

p.update(raceId=1,race5brainstonePos=-1,power=[0,2,1,0],knowledge=10,gold=20,ore=12,qic=8)
p['research'][1]=2
p['techs']=[{'techId':9,'isActionUsed':0,'isCovered':0}]
def projections():
    sorties={}
    analyze(d,sorties)
    return sorties
def etats(sorties,groupe,debut=''):
    return {e for (g,l),v in sorties.items() if g==groupe and l.startswith(debut) for e in v['bols']}

s=projections()
assert etats(s,'Recherche','Terraformation')=={Bols(0,0,2,1)}
assert etats(s,'Action technologique')=={Bols(0,0,1,2)}
assert any(v['offres'] for (g,l),v in s.items() if g=='Mine ordinaire')
assert all(not v['offres'] for (g,l),v in s.items() if g=='Recherche')
p['techs'][0]['isActionUsed']=1
assert not etats(projections(),'Action technologique')
p['research'][5]=4
assert charge_recherche(p,5)==6
d['gamestate'].update(name='stateIncomeChoice',args=[[1],[1]])
assert etats(projections(),'Revenus')==set(revenus(Bols.joueur(p),[1],[1]))
d['gamestate'].update(name='stateChargePwr',args=[3])
assert etats(projections(),'Charge passive','Charger')=={Bols(0,0,2,1)}

d=deepcopy(sample)
p=d['players']['1']
p.update(score=20,numShuttles=2,power=[0,2,1,0],qic=8,raceId=5,race5brainstonePos=2)
ship=d['board']['lostFleet']['ships'][0]
ship['playerIds']=[2]
assert Bols(0,0,3,0,0) in etats(projections(),'Explorer')
p.update(raceId=13,race5brainstonePos=-1)
assert Bols(0,0,1,1) in etats(projections(),'Explorer')
d['gamestate']['name']='statePlaceLost'
assert any(v['offres'] for v in projections().values())

from puissance import appliquer_reaction
adversaire={'power':[0,1,1,0],'raceId':1,'score':2,'buildings':{'9':0}}
choix,etat,_=list(reactions(adversaire,3))[1]
suivant=appliquer_reaction(adversaire,3,choix,etat)
assert suivant['power']==[0,0,0,2] and suivant['score']==0 and adversaire['score']==2
assert appliquer_reaction(adversaire,3,'Décliner',Bols.joueur(adversaire))['score']==2

# Recherche payée avec une conversion : charger les bols après la dépense.
d=deepcopy(sample)
p=d['players']['1']
p.update(power=[0,0,0,4],raceId=1,knowledge=3,ore=0,gold=0,qic=0)
p['research'][1]=2
assert etats(projections(),'Recherche','Terraformation')=={Bols(0,1,3,0)}
# L'ordre réel des lots peut créer une issue inaccessible en les fusionnant.
assert len(revenus(Bols(0,0,0,0),[1,1],[1]))==3

# Même case pour les quatre rangs, avec plafonnement par les bols.
d=deepcopy(sample)
p=d['players']['1']
p.update(raceId=1,score=20,numShuttles=3,qic=8,power=[0,3,0,0])
vaisseau=d['board']['lostFleet']['ships'][0]
case=next(h for row in d['map'].values() for h in row.values() if h['planetType']==vaisseau['type'])
cible=f"({case['q']}, {case['r']})"
for rang,n in enumerate([0,2,2,3]):
    vaisseau['playerIds']=[2,3,4][:rang]
    assert etats(projections(),'Explorer',cible)=={Bols(0,3-n,n,0)}
vaisseau['playerIds']=[1]
assert not etats(projections(),'Explorer',cible)

# Aucun gain adverse au placement initial ou à l'échange Ambas.
p['raceId']=6
assert all(not v['offres'] for (g,_),v in projections().items() if g=='Institut Ambas')
d['gamestate']['name']='stateSetupPlaceMine'
assert all(not v['offres'] for v in projections().values())

print('Charges, plafonds, conservation, ordre des revenus et déclencheurs vérifiés.')
