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
    if (p['raceId'] != 13 or p['buildings']['9'] or p['techs'] or p['fedTiles']
        or p['research'] != [0,0,0,0,0,0,3] or p['boosterId'] != 5
        or d['gamestate']['name'] != 'statePlayerTurn' or not board['config']['lostFleet']
        or p['score'] != 0 or p['numAvailGaiaformers'] or p['artifacts']):
        raise ValueError('Position hors du périmètre Nevlas validé. Étendre les règles avant de conclure.')
    ships = board['lostFleet']['ships']
    visited = [x for x in ships if pid in map(str,x['playerIds'])]
    if [x['type'] for x in visited] != [18]:
        raise ValueError('Configuration des vaisseaux à étendre.')
    cells = [h for row in d['map'].values() for h in row.values()]
    owned = [(h,b['buildingId']) for h in cells for b in h['buildings'] if str(b['playerId'])==pid]
    if sorted(b for _,b in owned) != [4,5,9] or board['roundNum'] != 2:
        raise ValueError('Configuration de bâtiments ou manche hors périmètre.')
    initial = (p['gold'],p['ore'],p['knowledge'],p['qic'],*p['power'][1:],p['power'][0])
    paths = reachable(initial)
    results = defaultdict(list)
    def add(group,label,c=0,o=0,k=0,q=0,power=0,tokens=0):
        for s,path in paths.items():
            if all(x>=y for x,y in zip(s,(c,o,k,q))) and 2*s[6]>=power and sum(s[4:7])>=tokens:
                cost=', '.join(f'{n} {u}' for n,u in zip((c,o,k,q,power,tokens),('cr','min','conn','QIC','puissance','jetons')) if n) or 'gratuit'
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
            ore=1+3*max(0,terra-steps)
            qic=max(0,ceil((dist-1-extra)/2))+(pt==8)
            name=PLANETS[pt] if pt<9 else 'Proto'
            add(mode,f"{name} ({h['q']}, {h['r']})",2,ore,price,qic,pw)
    for h,b in owned:
        xy=f"({h['q']}, {h['r']})"
        if b==4:
            neighbor=any(distance(z,h)<=2 and any(str(u['playerId'])!=pid and u['buildingId']>=4 for u in z['buildings']) for z in cells)
            add('Amélioration','Comptoir '+xy,3 if neighbor else 6,2)
        if b==5:
            for n,tech in enumerate(board['techs']):
                for track in ([TRACKS[n]] if n<6 else TRACKS):
                    add('Laboratoire',f'{xy} · technologie {tech} · {track}',5,3)
    for track in TRACKS:
        add('Recherche',track,k=4)
    for index,pw,label in [(1,3,'Gagner 2 jetons I'),(2,4,'Gagner 2 minerais'),(3,4,'Gagner 7 crédits'),(4,4,'Gagner 2 connaissances'),(5,7,'Gagner 3 connaissances')]:
        if free(index):
            add('Puissance',label,power=pw)
    for art in visited[0]['availArtifacts']:
        if art:
            effects={7:'3 PV + 1 PV par type colonisé', 10:'5 crédits et 2 minerais', 6:'3 PV par secteur extérieur colonisé'}
            add('Artefact',f'Crépuscule · {effects.get(art,art)}',tokens=6)
    for boost in board['availBoosters']:
        add('Passer',f'Booster {boost} · '+{7:'comptoirs',8:'laboratoires',9:'institut et académies'}.get(boost,''))
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
