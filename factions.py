"""Règles de faction appliquées à l'état BGA du joueur actif."""
from functools import lru_cache
from conversions import Conversions

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

def payment_solver(p, fleet, avec_bols=False):
    """Premier témoin du même parcours que les paiements détaillés."""
    conversions=Conversions(p,fleet)

    @lru_cache(None)
    def solve(c,o,k,q,power,tokens,formers=0):
        cout=(c,o,k,q,power,tokens,formers)
        for chemin,avant,_ in conversions.parcours(cout):
            return (chemin,avant.bols) if avec_bols else chemin
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
