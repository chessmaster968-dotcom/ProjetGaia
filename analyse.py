"""Gaia Project, analyseur v0.1. Python 3.10+. Sortie Markdown sur stdout.
Usage : python analyse.py coup61.json
Périmètre testé : position Nevlas du coup 61, extension Flotte perdue.
Références : règles Capstone, client public BGA Gaia Project 260921-2211
(modules gpj-actions, map, bonusTiles, research, factions, ui).
"""
import json
import sys
from collections import deque, defaultdict
from pathlib import Path
from math import ceil
from objectifs import bonus_manche, technologies, pistes, compteurs, gains_technologie, EFFETS

TRACKS = ['Terraformation', 'Navigation', 'IA', 'Projet Gaia', 'Économie', 'Science']
PLANETS = ['Espace','Terra','Oxyde','Volcanique','Désert','Marais','Titane','Glace','Gaia']
# Ressources suivies durant les conversions : crédits, minerai, connaissance, QIC,
# jetons I, II, III, Gaia. Les témoins ne gaspillent pas de ressources à dessein.
def conversions(s):
    c,o,k,q,i,j,t,g = s
    if j >= 2:
        yield 'sacrifier en bol II', (c,o,k,q,i,j-2,t+1,g)
    if t:
        yield 'III vers Gaia pour 1 connaissance', (c,o,k+1,q,i,j,t-1,g+1)
        yield '1 jeton III pour 2 crédits', (c+2,o,k,q,i+1,j,t-1,g)
    if t >= 2:
        for label,do,dk,dq in [('1 minerai',1,0,0),('1 connaissance',0,1,0),('1 QIC',0,0,1)]:
            yield '2 jetons III pour '+label,(c,o+do,k+dk,q+dq,i+2,j,t-2,g)
    if q:
        yield '1 QIC pour 1 minerai',(c,o+1,k,q-1,i,j,t,g)
    if o:
        yield '1 minerai pour 1 crédit',(c+1,o-1,k,q,i,j,t,g)
        yield '1 minerai pour 1 jeton I',(c,o-1,k,q,i+1,j,t,g)
    if k:
        yield '1 connaissance pour 1 crédit',(c+1,o,k-1,q,i,j,t,g)

def reachable(initial):
    paths = {initial: ()}
    queue = deque([initial])
    while queue:
        current = queue.popleft()
        for label, state in conversions(current):
            if state not in paths:
                paths[state] = paths[current] + (label,)
                queue.append(state)
    return paths

def distance(a,b):
    dq,dr = a['q']-b['q'], a['r']-b['r']
    return max(abs(dq),abs(dr),abs(dq+dr))

def analyze(d):
    pid = str(d['gamestate']['active_player'])
    p = d['players'][pid]
    board = d['board']
    if (p['raceId'] != 13 or p['buildings']['9']
        or p['boosterId'] != 5
        or d['gamestate']['name'] != 'statePlayerTurn' or not board['config']['lostFleet']
        or p['numAvailGaiaformers'] or p['artifacts']):
        raise ValueError('Position hors du périmètre Nevlas validé. Étendre les règles avant de conclure.')
    ships = board['lostFleet']['ships']
    visited = [x for x in ships if pid in map(str,x['playerIds'])]
    if not any(x['type']==18 for x in visited):
        raise ValueError('Configuration des vaisseaux à étendre.')
    cells = [h for row in d['map'].values() for h in row.values()]
    owned = [(h,b['buildingId']) for h in cells for b in h['buildings'] if str(b['playerId'])==pid]
    if sorted(b for _,b in owned) != [4,5,9]:
        raise ValueError('Configuration de bâtiments ou manche hors périmètre.')
    initial = (p['gold'],p['ore'],p['knowledge'],p['qic'],*p['power'][1:],p['power'][0])
    paths = reachable(initial)
    results = defaultdict(list)
    metrics=compteurs(d,pid)[1]
    def add(group,label,c=0,o=0,k=0,q=0,power=0,tokens=0,events=None,tech=None,cover=None):
        for s,path in paths.items():
            if all(x>=y for x,y in zip(s,(c,o,k,q))) and 2*s[6]>=power and sum(s[4:7])>=tokens:
                cost=', '.join(f'{n} {u}' for n,u in zip((c,o,k,q,power,tokens),('cr','min','conn','QIC','puissance','jetons')) if n) or 'gratuit'
                events=events or {}
                vp=bonus_manche(board,events)
                active={t['techId'] for t in p['techs'] if not t.get('isCovered')} - {cover}
                if tech in EFFETS:
                    post=dict(metrics)
                    if events.get('laboratoire'):
                        post['comptoirs']-=1
                        post['laboratoires']+=1
                    immediate=gains_technologie(tech,'acquisition',post)
                    vp+=immediate.get('PV',0)
                    for unit,n in immediate.items():
                        if unit!='PV': label+=f' · +{n} {unit}'
                    active.add(tech)
                for tile in active & EFFETS.keys():
                    for event,times in events.items():
                        vp+=gains_technologie(tile,event,metrics,times).get('PV',0)
                vp+=7*(tech==3)
                vp+=3*events.get('mine Gaia',0)*(4 in active)
                label+=f' · +{vp} PV (manche et technologies)'
                results[group].append((label,cost,' → '.join(path) or 'direct'))
                return
    def free(index):
        return not board['usedActions'][index]
    for h in cells:
        pt=h['planetType']
        if h['buildings'] or pt not in [1,2,3,4,5,6,7,8,12]:
            continue
        dist=min(distance(h,a) for a,_ in owned)
        for mode,action,extra,steps,price,pw in [
            ('Mine ordinaire',0,0,0,0,0),('Mine avec 1 étape offerte',11,0,1,0,3),
            ('Mine avec 2 étapes offertes',12,0,2,0,5),('Mine via le Crépuscule',37,3,0,1,0)]:
            if action and not free(action):
                continue
            terra = 3 if pt==12 else 0 if pt==8 else min(7-pt,pt)
            if steps and (pt == 8 or terra == 0):
                continue
            ore=1+[3,3,2,1,1,1][p["research"][1]]*max(0,terra-steps)
            qic=max(0,ceil((dist-[1,1,2,2,3,4][p["research"][2]]-extra-int(any(t["techId"]==41 and not t.get("isCovered") for t in p["techs"])))/2))+(pt==8)
            name=PLANETS[pt] if pt<9 else 'Proto'
            add(mode,f"{name} ({h['q']}, {h['r']})",2,ore,price,qic,pw,events={
                'mine':1,'mine Gaia':int(pt==8),'étape':terra,
                'nouveau secteur':int((h['tileNum']<100 or h['tileNum']>=200) and all(a['tileNum']!=h['tileNum'] for a,_ in owned)),
                'nouveau type':int(all(a['planetType']!=pt for a,_ in owned))})
    for h,b in owned:
        xy=f"({h['q']}, {h['r']})"
        if b==4:
            neighbor=any(distance(z,h)<=2 and any(str(u['playerId'])!=pid and u['buildingId']>=4 for u in z['buildings']) for z in cells)
            add('Amélioration','Comptoir '+xy,3 if neighbor else 6,2,events={"comptoir":1})
        if b==5:
            for tech,cover,tracks in technologies(d,pid)[0]:
                for track in tracks:
                    target=TRACKS[track-1] if track else 'aucune progression'
                    payment=f' · recouvrir {cover} et retourner une Alliance' if cover else ''
                    if track and p['research'][track]==4:
                        payment+=' · retourner une Alliance pour le niveau 5'
                    add('Laboratoire',f'{xy} · technologie {tech} · {target}{payment}',5,3,
                        events={'laboratoire':1,'recherche':int(bool(track))},tech=tech,cover=cover)
    for track in pistes(d,pid):
        add('Recherche',TRACKS[track-1],k=4,events={'recherche':1})
    for index,pw,label in [(1,3,'Gagner 2 jetons I'),(2,4,'Gagner 2 minerais'),(3,4,'Gagner 7 crédits'),(4,4,'Gagner 2 connaissances'),(5,7,'Gagner 3 connaissances')]:
        if free(index):
            add('Puissance',label,power=pw)
    for tile in p['techs']:
        tid=tile['techId']
        if tid in (10,11,12) and not tile.get('isCovered') and not tile['isActionUsed']:
            reward=gains_technologie(tid,'action',metrics)
            add('Action technologique',' + '.join(f'{v} {u}' for u,v in reward.items()))
    for art in next(x for x in visited if x['type']==18)['availArtifacts']:
        if art:
            effects={7:'3 PV + 1 PV par type colonisé', 10:'5 crédits et 2 minerais', 6:'3 PV par secteur extérieur colonisé'}
            add('Artefact',f'Crépuscule · {effects.get(art,art)}',tokens=6)
    for boost in board['availBoosters']:
        add('Passer',f'Booster {boost} · '+{7:'comptoirs',8:'laboratoires',9:'institut et académies'}.get(boost,''),events={'passage':1})
    return results

if __name__=='__main__':
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
    results=analyze(data)
    print('# Projet Gaia · coup',data['notifications']['move_nbr'])
    print('\nUne ligne par action, cible et mode. Une préparation possible est indiquée. Les gains, choix de paiement alternatifs et réactions adverses ne sont pas simulés.\n')
    for group,rows in results.items():
        print(f'## {group} ({len(rows)})\n\n| Choix | Coût principal | Préparation |\n|---|---|---|')
        for row in rows: print('| '+' | '.join(row)+' |')
        print()
