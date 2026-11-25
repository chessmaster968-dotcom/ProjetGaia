"""Règles de faction appliquées à l'état BGA du joueur actif."""
from collections import deque
from functools import lru_cache

NAMES = ('','Terraniens','Lantides','Xenos','Gleens','Taklons','Ambas','Hadsch Hallas',
         'Ivits','Géodens','Bal T’aks','Firaks','Bescods','Nevlas','Itars','Tinkéroïdes',
         'Darkaniens','Moweyds','Géants de l’espace')
HOME = (0,1,1,4,4,5,5,2,2,3,3,6,6,7,7,11,11,12,12)

def institute(p):
    return int(p['buildings']['9']) == 0

def terraforming(p, planet):
    race=p['raceId']
    if planet in (8,11):
        return 0
    if planet==12:
        return 3
    if race in (15,17):
        return 3 if planet in p['terraBoard'] else 1
    if race in (16,18):
        return 1 if race==16 else 2
    difference=abs(planet-HOME[race])
    return min(difference,7-difference)

def qic_income(p):
    return not (p['raceId']==4 and p['buildings']['8']>0)

def payment_solver(p, fleet):
    """Un témoin de paiement par coût. Les transformations explorées sont
    orientées vers le déficit courant pour éviter de permuter les gaspillages."""
    race=p['raceId']; pi=institute(p)
    multiplier=2 if race==13 and pi else 1
    start=(p['gold'],p['ore'],p['knowledge'],p['qic'],*p['power'][1:4],
           p.get('race5brainstonePos',-1),p['numAvailGaiaformers'])

    @lru_cache(None)
    def solve(c,o,k,q,power,tokens,formers=0):
        queue=deque([(start,())]); seen={start}
        while queue:
            state,path=queue.popleft()
            gold,ore,know,qic,i,j,t,brain,gaia=state
            spend=t*multiplier+3*(brain==3)
            physical=i+j+t+int(brain in (1,2,3))
            if (gold>=c and ore>=o and know>=k and qic>=q and spend>=power
                    and physical>=tokens and gaia>=formers):
                return path
            def push(label, changes, newbrain=None):
                nxt=list(state)
                for index,delta in changes.items(): nxt[index]+=delta
                if newbrain is not None: nxt[7]=newbrain
                if any(nxt[x]<0 for x in (0,1,2,3,4,5,6,8)): return
                limit=(30,15,15)
                for idx,maximum in enumerate(limit): nxt[idx]=min(maximum,nxt[idx])
                nxt=tuple(nxt)
                if nxt not in seen:
                    seen.add(nxt);queue.append((nxt,path+(label,)))
            if j>=2:
                label='sacrifier en bol II' + (' · jeton sacrifié vers Gaia' if race==14 else '')
                push(label,{5:-2,6:1})
            if brain==2 and j>=1:
                push('sacrifier pour charger la pierre-esprit',{5:-1},3)
            needs=(gold<c,ore<o or (ore<=o and physical<tokens),know<k,qic<q)
            for idx,(units,label) in enumerate([(1,'crédit'),(3,'minerai'),(4,'connaissance'),(4,'QIC')]):
                if not needs[idx] or (idx==3 and not qic_income(p)): continue
                n=(units+multiplier-1)//multiplier
                gain=2 if idx==0 and multiplier==2 else 1
                if t>=n: push(f'{n} jeton(s) III → {gain} {label}',{6:-n,4:n,idx:gain})
                if brain==3 and t>=max(0,units-3):
                    extra=max(0,units-3)
                    push(f'pierre-esprit → {label}',{6:-extra,4:extra,idx:1},1)
                if race==7 and pi and idx and gold>=units:
                    push(f'{units} crédits → {label}',{0:-units,idx:1})
            if race==13 and know<k and t:
                push('III vers Gaia pour 1 connaissance',{6:-1,2:1})
            if race==10 and qic<q and gaia>formers:
                push('gaiaformeur vers Gaia pour 1 QIC',{8:-1,3:1})
            if race==3 and fleet and ore and (spend<power or physical<tokens or any(needs)):
                push('1 minerai → 1 jeton III',{1:-1,6:1})
            if qic>q and (ore<o or physical<tokens or gold<c):
                push('1 QIC → 1 minerai',{3:-1,1:1})
            if ore and physical<tokens: push('1 minerai → 1 jeton I',{1:-1,4:1})
            if gold<c and ore>o: push('1 minerai → 1 crédit',{1:-1,0:1})
            if gold<c and know>k: push('1 connaissance → 1 crédit',{2:-1,0:1})
        return None
    return solve

def structure_power(p, h, b):
    """Puissance de la pièce pour une fédération (satellite = 0)."""
    kind=b['buildingId']
    base={3:1,4:1,5:2,6:2,7:3,8:3,9:3}.get(kind,0)
    if kind>=7 and any(t['techId']==5 and not t.get('isCovered') for t in p['techs']):
        base+=1
    if p['raceId']==12 and institute(p) and h['planetType']==6 and kind>=4:
        base+=1
    return base+2*int(bool(b.get('hasRing')))

def federation_without_satellites(d,pid,distance):
    """Composantes connexes déjà en contact. Une même grappe doit rester entière."""
    p=d['players'][pid]
    if p['raceId']==8 and any(b.get('isPartOfFed') for row in d['map'].values()
           for h in row.values() for b in h['buildings'] if str(b['playerId'])==pid):
        return
    cells=[(h,b) for row in d['map'].values() for h in row.values() for b in h['buildings']
           if str(b['playerId'])==pid and b['buildingId']>=3 and not b['isPartOfFed']]
    existing=[h for row in d['map'].values() for h in row.values()
              if any(str(b['playerId'])==pid and b['isPartOfFed'] for b in h['buildings'])]
    threshold=6 if p['raceId']==3 and institute(p) else 7
    while cells:
        cluster=[cells.pop()]
        for h,_ in cluster:
            neighbors=[v for v in cells if distance(h,v[0])<=1]
            cluster.extend(neighbors)
            for v in neighbors: cells.remove(v)
        if any(distance(h,old)<=1 for h,_ in cluster for old in existing): continue
        if sum(structure_power(p,h,b) for h,b in cluster)>=threshold:
            yield ' + '.join(f"({h['q']}, {h['r']})" for h,_ in cluster)
