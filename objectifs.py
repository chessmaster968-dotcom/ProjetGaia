"""Règles des objectifs et technologies. Les identifiants sont ceux de BGA."""
import json
import sys
from factions import NAMES
from pathlib import Path

PISTES = ['Terraformation', 'Navigation', 'IA', 'Projet Gaia', 'Économie', 'Science']
MANCHES = [None, ('étape',2), ('recherche',2), ('mine',2), ('alliance',5),
           ('comptoir',3), ('comptoir',4), ('mine Gaia',3), ('mine Gaia',4),
           ('académie ou institut',5), ('académie ou institut',5), ('nouveau secteur',3),
           ('nouveau type',3), ('laboratoire',4)]
FIN = ['','Bâtiments en alliance','Bâtiments','Types de planètes','Planètes Gaia',
       'Secteurs ordinaires','Satellites et stations spatiales','Astéroïdes',
       'Distance maximale institut–académie','Secteurs de l’espace lointain']
# Déclencheur, unité de mesure, quantité et ressource produite.
EFFETS = {
    10:('action','fois',1,'QIC + 5 crédits'),11:('action','fois',3,'minerais'),
    12:('action','fois',3,'connaissances'),13:('acquisition','mines',2,'PV'),
    14:('acquisition','secteurs',1,'minerais'),15:('acquisition','secteurs',2,'PV'),
    16:('acquisition','Gaia',2,'PV'),17:('acquisition','tuiles Alliance',5,'PV'),
    18:('acquisition','comptoirs',4,'PV'),19:('passage','tuiles Alliance',3,'PV'),
    20:('passage','laboratoires',3,'PV'),21:('passage','types',1,'PV'),
    22:('recherche','fois',2,'PV'),23:('mine','fois',3,'PV'),
    24:('comptoir','fois',3,'PV'),30:('acquisition','instituts et académies',6,'PV'),
    31:('acquisition','secteurs lointains',4,'PV'),32:('passage','secteurs lointains',2,'PV'),
    33:('passage','astéroïdes',2,'PV'),34:('étape','fois',2,'PV'),35:('action QIC','fois',4,'PV')}
STANDARD = set(range(1,10)) | {40,41,42}

def bonus_manche(board, events):
    n=board['roundNum']
    if not 1 <= n <= 6:
        return 0
    event, rate=MANCHES[board['roundBonus'][n]]
    return rate * events.get(event,0)

def compteurs(d,pid):
    p=d['players'][str(pid)]
    pieces=[(h,b) for row in d['map'].values() for h in row.values()
            for b in h['buildings'] if str(b['playerId'])==str(pid)]
    structures=[(h,b) for h,b in pieces if b['buildingId']>=4]
    planets=[h for h,b in structures if p['raceId']!=2 or not any(
        str(x['playerId'])!=str(pid) and x['buildingId']>=4 for x in h['buildings'])]
    artifacts=set(p['artifacts'])
    virtual={t for a,t in [(1,11),(2,12)] if a in artifacts}
    types={h['planetType'] for h in planets}|virtual
    sectors={h['tileNum'] for h,b in structures}
    dist=max((max(abs(q:=a['q']-b['q']),abs(r:=a['r']-b['r']),abs(q+r))
              for a,x in structures if x['buildingId']==9
              for b,y in structures if y['buildingId'] in (7,8)),default=0)
    def count(*ids):
        return sum(b['buildingId'] in ids for _,b in structures)
    final=[0,sum(bool(b['isPartOfFed']) for _,b in structures),len(structures)+len(virtual),
           len(types),sum(h['planetType']==8 for h in planets),sum(0<s<100 for s in sectors),
           sum(b['buildingId'] in (1,3) for _,b in pieces),
           sum(h['planetType']==11 for h in planets)+(11 in virtual),dist,sum(s>=200 for s in sectors)]
    metrics={'fois':1,'Gaia':final[4],'secteurs':final[5],'secteurs lointains':final[9],
             'astéroïdes':final[7],'types':final[3],'mines':count(4)+len(virtual),
             'instituts et académies':count(7,8,9),'tuiles Alliance':len(p['fedTiles']),
             'comptoirs':count(5),'laboratoires':count(6)}
    return final,metrics

def gains_technologie(tile, event, metrics, occurrences=1):
    trigger,unit,rate,resource=EFFETS[tile]
    if trigger!=event:
        return {}
    if tile==10:
        return {'QIC':occurrences,'crédits':5*occurrences}
    return {resource:occurrences*rate*metrics[unit]}

def pistes(d,pid,green_spent=0):
    p=d['players'][str(pid)]
    green=sum(bool(t['isGreen']) for t in p['fedTiles'])-green_spent
    return [i for i in range(1,7) if p['research'][i]<5
            and not (p['raceId']==10 and i==2 and p['buildings']['9'])
            and (p['research'][i]<4 or (green>0 and all(
                opp['research'][i]<5 for opp in d['players'].values())))]

def technologies(d,pid):
    """Choix lors d'un gain de technologie. Vérifie l'accès avant la progression."""
    b=d['board']; p=d['players'][str(pid)]
    fleet=b.get('lostFleet') or {}
    ships=[s for s in fleet.get('ships',[]) if str(pid) in map(str,s['playerIds'])]
    held={n for t in p['techs'] for n in (t['techId'],t.get('coveredTechId',0))}
    covers=sorted(t['techId'] for t in p['techs'] if t['techId'] in STANDARD and not t.get('isCovered'))
    normal=pistes(d,pid)
    choices=[]
    for i,tile in enumerate(b['techs']+[s['availTech'] for s in ships if s.get('availTech')]):
        if tile and tile not in held:
            tracks=([i+1] if i+1 in normal else []) if i<6 else normal
            choices.append((tile,None,tracks or [0]))
    details=[]
    for i,tile in enumerate(b['advTechs']):
        reasons=[]
        if not tile: reasons.append('Tuile déjà prise')
        if i<6 and p['research'][i+1]<4: reasons.append('Niveau 4 ou 5 en '+PISTES[i])
        if i==6:
            if not b['config'].get('lostFleet'): reasons.append('Extension requise')
            elif fleet['scoreBoard']:
                if len({s['type'] for s in ships})<3: reasons.append(f'{len(ships)}/3 vaisseaux explorés')
            elif p['score']<25: reasons.append(f"{p['score']}/25 PV")
        if not covers: reasons.append('Une technologie standard découverte à recouvrir')
        if not any(t['isGreen'] for t in p['fedTiles']): reasons.append('Une tuile Alliance verte à retourner')
        details.append((tile,reasons))
        if not reasons:
            choices.extend((tile,cover,pistes(d,pid,1) or [0]) for cover in covers)
    return choices,details

def prendre_avancee(d,pid,tile,cover,track,alliances,*,pierre_en_premier=None):
    """Retourne une copie après acquisition. Les autres effets du bâtiment et les
    récompenses de piste sont résolus par l'action appelante. Les indices de
    jetons permettent de choisir quelles alliances retourner."""
    from copy import deepcopy
    options,_=technologies(d,pid)
    if not any(t==tile and c==cover and c is not None and track in tracks
               for t,c,tracks in options):
        raise ValueError('Acquisition ou progression indisponible')
    p=d['players'][str(pid)]
    needed=1+int(bool(track) and p['research'][track]==4)
    if (len(alliances)!=needed or len(set(alliances))!=needed or
            any(i<0 or i>=len(p['fedTiles']) or not p['fedTiles'][i]['isGreen'] for i in alliances)):
        raise ValueError('Paiement en tuiles Alliance invalide')
    out=deepcopy(d)
    after=out['players'][str(pid)]
    for i in alliances:
        after['fedTiles'][i]['isGreen']=0
    supply=out['board']['advTechs']
    supply[supply.index(tile)]=0
    base=next(t for t in after['techs'] if t['techId']==cover)
    base['isCovered']=1
    after['techs'].append({'techId':tile,'isCovered':0,'coveredTechId':cover,'isActionUsed':0})
    if track:
        from puissance import Bols, charge_recherche
        charge=charge_recherche(p,track)
        if charge:
            depart=Bols.joueur(after)
            premier=depart.charger(charge,True)[0]
            dernier=depart.charger(charge,False)[0]
            if premier!=dernier and pierre_en_premier is None:
                raise ValueError('Choisir la priorité de charge de la pierre-esprit')
            etat=premier if pierre_en_premier else dernier
            after=out['players'][str(pid)]=etat.appliquer(after)
        after['research'][track]+=1
    metrics=compteurs(out,pid)[1]
    for unit,n in gains_technologie(tile,'acquisition',metrics).items():
        if unit=='minerais': after['ore']=min(15,after['ore']+n)
        else: after['score']+=n
    return out

def classement(values):
    prizes=[18,12,6,0]
    return {p:sum(prizes[rank:rank+ties])//ties for p,v in values.items()
            for rank in [sum(other>v for other in values.values())]
            for ties in [list(values.values()).count(v)]}

def synthese(d):
    b=d['board']; pid=d['gamestate']['active_player']
    players=d['players']
    stats={p:compteurs(d,p)[0] for p in players}
    finals=[]
    for i in b['endGameBonus']:
        values={p:v[i] for p,v in stats.items()}
        if len(players)==2:
            values['neutre']=[0,10,11,6 if b['config'].get('lostFleet') else 5,4,6,8,3,8,3][i]
        scores=classement(values)
        finals.append({'objectif':FIN[i],'compteurs':values,'pv':scores})
    advanced=[]
    for i,(tile,reasons) in enumerate(technologies(d,pid)[1]):
        effect='Tuile épuisée'
        if tile:
            when,unit,rate,resource=EFFETS[tile]
            effect=f'{when} · {rate} {resource}'+(' par '+unit if unit!='fois' else '')
        advanced.append({'piste':(PISTES+['Flotte perdue'])[i],'tuile':tile,'effet':effect,'conditions':reasons})
    return {'faction':NAMES[players[str(pid)]['raceId']], 'manches':[f'{rate} PV · {event}' for k in b['roundBonus'][1:] for event,rate in [MANCHES[k]]],
            'objectifs':finals,'avancees':advanced}
if __name__=='__main__':
    print(json.dumps(synthese(json.loads(Path(sys.argv[1]).read_text())),ensure_ascii=False,indent=2))
