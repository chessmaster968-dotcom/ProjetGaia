"""Gaia Project, analyseur v0.3. Python 3.10+. Sortie Markdown sur stdout.
Usage : python analyse.py coup61.json
Moteur multifaction, jeu de base et extension Flotte perdue.
Références : règles Capstone, client public BGA Gaia Project 260921-2211
(modules gpj-actions, map, bonusTiles, research, factions, ui).
"""
import json
from argparse import ArgumentParser
from itertools import islice
from conversions import Conversions
from collections import defaultdict
from dataclasses import replace
from puissance import Bols, reactions, revenus, charge_recherche
from pathlib import Path
from math import ceil
from objectifs import bonus_manche, technologies, pistes, compteurs, gains_technologie, EFFETS

TRACKS = ['Terraformation', 'Navigation', 'IA', 'Projet Gaia', 'Économie', 'Science']
PLANETS = ['Espace','Terra','Oxyde','Volcanique','Désert','Marais','Titane','Glace','Gaia']
from factions import NAMES, HOME, institute, terraforming, payment_solver, qic_income, federation_without_satellites, structure_power

def distance(a,b):
    dq,dr = a['q']-b['q'], a['r']-b['r']
    return max(abs(dq),abs(dr),abs(dq+dr))

def analyze(d, projections=None):
    pid = str(d['gamestate']['active_player'])
    p = d['players'][pid]
    board = d['board']
    race=int(p['raceId'])
    if not 1 <= race < len(NAMES): raise ValueError('Faction inconnue')
    pi=institute(p)
    fleet=bool(board.get('config',{}).get('lostFleet'))
    ships=(board.get('lostFleet') or {}).get('ships',[])
    visited=[x for x in ships if pid in map(str,x['playerIds'])]
    twilight=next((x for x in visited if x['type']==18),{})
    cells = [h for row in d['map'].values() for h in row.values()]
    owned = [(h,b['buildingId']) for h in cells for b in h['buildings'] if str(b['playerId'])==pid]
    colonies=[(h,b) for h,b in owned if b>=4]
    origins=[h for h,b in owned if b>=3]
    pay=payment_solver(p,fleet,avec_bols=True)
    results = defaultdict(list)
    metrics=compteurs(d,pid)[1]
    def voisinage(h):
        offres = {}
        for case in cells:
            if distance(h,case)>2:
                continue
            for piece in case['buildings']:
                autre=str(piece['playerId'])
                if autre==pid or autre not in d['players'] or piece['buildingId']<4:
                    continue
                valeur=structure_power(d['players'][autre],case,piece)
                offres[autre]=max(valeur,offres.get(autre,0))
        return offres

    def add(group,label,c=0,o=0,k=0,q=0,power=0,tokens=0,events=None,tech=None,cover=None,formers=0,
            charge=0, track=0, construit=None, pierre_gaia=False, fins=None, gaia_itars=False):

        payment=pay(c,o,k,q,power,tokens,formers)
        if payment is not None:
            path, depart=payment
            cost=', '.join(f'{n} {u}' for n,u in zip((c,o,k,q,power,tokens,formers),('cr','min','conn','QIC','puissance','jetons','gaiaformeur')) if n) or 'gratuit'
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
            charge+=charge_recherche(p,track)
            if charge or pierre_gaia or group=='Explorer':
                if gaia_itars:
                    depart=replace(depart,gaia=depart.gaia-4)
                if pierre_gaia:
                    depart=replace(depart,pierre=0)
                multiplicateur=2 if race==13 and pi else 1
                fins=sorted({etat.charger(charge,priorite)[0]
                             for etat in depart.payer(power,tokens,multiplicateur)
                             for priorite in (False,True)})
                if not fins:
                    return
            offres=voisinage(construit) if construit else {}
            if offres:
                descriptions=[]
                for j,n in offres.items():
                    possibles=list(reactions(d['players'][j],n))
                    couts=[prix for nom,etat,prix in possibles if nom!='Décliner']
                    maximum=max(couts)+1 if couts else 0
                    descriptions.append(f'J{j} {maximum}/{n} ({max(couts,default=0)} PV max.)')
                label+=' · charge passive possible/offerte '+', '.join(descriptions)
            if fins:
                label+=(' · charge '+str(charge) if charge else '')+' · '+' ou '.join(x.description() for x in fins)
            if projections is not None:
                projections[group,label]={'bols':tuple(fins or ()), 'offres':offres,
                    'cout':(c,o,k,q,power,tokens,formers), 'vers_gaia':group=='Projet Gaia'}
            results[group].append((label,cost,' → '.join(path) or 'direct'))
            return
    def free(index):
        return index<len(board['usedActions']) and not board['usedActions'][index]
    def tech_choices(group,label,c=0,o=0,events=None,**options):
        for tech,cover,tracks in technologies(d,pid)[0]:
            for track in tracks:
                target=TRACKS[track-1] if track else 'aucune progression'
                payment=f' · recouvrir {cover} et retourner une Alliance' if cover else ''
                if track and p['research'][track]==4:
                    payment+=' · retourner une Alliance pour le niveau 5'
                add(group,f'{label} · technologie {tech} · {target}{payment}',c,o,
                    events={**(events or {}),'recherche':int(bool(track))},tech=tech,cover=cover,track=track,**options)

    phase=d['gamestate']['name']
    if phase in ('stateSetupPlacePI','stateSetupPlaceMine'):
        kind='Institut' if race in (8,15) else 'Mine'
        for h in cells:
            if h['planetType']==HOME[race] and not h['buildings']:
                add('Placement initial',f"{kind} ({h['q']}, {h['r']})")
        return results
    if phase in ('stateIncome','stateIncomeChoice'):
        args=d['gamestate'].get('args') or []
        inc=d.get('income',{}).get(pid)
        if len(args)>=2 and all(isinstance(x,list) for x in args[:2]):
            # BGA presents only the lots still awaiting a decision.
            fins=revenus(Bols.joueur(p),args[0],args[1])
        elif inc:
            fins=revenus(Bols.joueur(p),inc[4],inc[5],sum(inc[6]) if len(inc)>6 else 0)
        else:
            fins=None
        if race==15 and not p.get('activeTinkerTokenId'):
            eligible=range(1,4) if board['roundNum']<=3 else range(4,7)
            for tile in p['remainingTinkerTokens']:
                if tile in eligible: add('Bricolage',f'Choisir la tuile {tile}',fins=fins)
        elif fins:
            for etat in fins: add('Revenus','Percevoir',fins=[etat])
        else:
            raise ValueError('Lots de puissance des revenus absents de cet export')
        return results
    if phase=='stateSetupChooseBooster':
        for booster in board['availBoosters']: add('Booster initial',f'Booster {booster}')
        return results
    if phase=='stateGainTech':
        tech_choices('Technologie','Acquérir')
        return results
    if phase=='stateChargePwr':
        offer=int(d['gamestate']['args'][0])
        for choix,etat,cout in reactions(p,offer):
            add('Charge passive',choix,fins=[etat])
        return results
    if phase=='stateGaiaRace14' and race==14:
        add('Phase Gaia','Conserver les jetons')
        if pi and p['power'][0]>=4: tech_choices('Phase Gaia','Défausser 4 jetons Gaia',gaia_itars=True)
        return results
    if phase=='stateGaiaRace1' and race==1:
        pool=p['power'][0]
        for q in range(pool//4+1 if pi else 1):
            for k in range((pool-4*q)//4+1 if pi else 1):
                for o in range((pool-4*q-4*k)//3+1 if pi else 1):
                    for c in range(pool-4*q-4*k-3*o+1 if pi else 1):
                        add('Phase Gaia',f'{pool} jetons en II · {c} crédits, {o} minerais, {k} connaissances, {q} QIC')
        return results
    if phase=='stateResearchAdv':
        for track in pistes(d,pid):
            add('Recherche offerte',TRACKS[track-1],track=track,events={'recherche':1})
        add('Recherche offerte','Renoncer')
        return results
    if phase not in ('statePlayerTurn','stateExtraMineBuild','statePlaceLost'): raise ValueError('Phase hors analyse des tours d’action')
    modes=[('Mine ordinaire',0,0,0,0,0),('Mine avec 1 étape offerte',11,0,1,0,3),
           ('Mine avec 2 étapes offertes',12,0,2,0,5)]
    if twilight: modes.append(('Mine via le Crépuscule',37,3,0,1,0))
    if p['boosterId']==1: modes.append(('Booster terraformation',13,0,1,0,0))
    if p['boosterId']==2: modes.append(('Booster portée',14,3,0,0,0))
    if fleet and race==4: modes.append(('Exploration Gleens',16,2,0,0,0))
    if fleet and race==18: modes.append(('Exploration des Géants',17,0,2,0,0))
    types_visites={v['type'] for v in visited}
    if 16 in types_visites: modes.append(('Mine via T. F. Mars',35,0,1,0,0))
    if 15 in types_visites: modes.append(('Astéroïde via Éclipse',36,0,0,0,0))
    special_ready=not p['hasUsedPiAction']
    tink=p.get('activeTinkerTokenId',0)
    if race==15 and pi and special_ready and tink in (1,4):
        modes.append(('Bricolage',45,0,{1:1,4:3}[tink],0,0))
    reach=[1,1,2,2,3,4][p['research'][2]]+int(any(
        t['techId']==41 and not t.get('isCovered') for t in p['techs']))
    def range_cost(h,bonus=0):
        dist=min((distance(h,a) for a in origins),default=999)
        return max(0,ceil((dist-reach-bonus)/2))
    extra_mine = board.get('lostFleet') or {}
    bonus_mine=phase=='stateExtraMineBuild'
    gratuite=bonus_mine and extra_mine.get('extraMineFree',0)
    if phase=='statePlaceLost':
        for h in cells:
            if h['planetType']==0 and not h['buildings']:
                add('Planète perdue',f"Mine ({h['q']}, {h['r']})",q=range_cost(h),construit=h,events={'mine':1})
        return results
    if bonus_mine:
        modes=[('Mine bonus',0,extra_mine.get('extraMineDist',0),extra_mine.get('extraMineSteps',0),0,0)]
    for h in cells:
        pt=h['planetType']; pieces=h['buildings']; xy=f"({h['q']}, {h['r']})"
        shared=race==2 and pieces and all(str(b['playerId'])!=pid and b['buildingId']>=4 for b in pieces)
        gaiaformed=any(str(b['playerId'])==pid and b['buildingId']==2 for b in pieces) and pt==8
        if (pt not in range(1,13) or pt==9 or pt==10 and not shared
                or pieces and not (shared or gaiaformed) or not p['buildings']['4']): continue
        newtype=all(a['planetType']!=pt for a,_ in colonies)
        newsector=not 100<=h['tileNum']<200 and all(a['tileNum']!=h['tileNum'] for a,_ in colonies)
        for mode,action,extra,steps,price,pw in modes:
            if action and not free(action): continue
            terra=0 if shared or gaiaformed else terraforming(p,pt)
            if steps and terra==0 and not bonus_mine: continue
            if action==36 and (pt!=11 or shared): continue
            asteroid=pt==11 and not shared
            ore=int(not asteroid and not gratuite)+[3,3,2,1,1,1][p['research'][1]]*max(0,terra-steps)
            qic=0 if gaiaformed else range_cost(h,extra)
            if pt==8 and not shared and not gaiaformed:
                if race==4: ore+=1
                else: qic+=2 if race in (15,16,18) else 1
            name=PLANETS[pt] if pt<9 else {10:'Perdue',11:'Astéroïde',12:'Proto'}[pt]
            label=f'{name} {xy}'
            if race==2 and pi and (shared or fleet and len(d['players'])<=2 and pt==HOME[race]):
                label+=' · +2 connaissances'
                if fleet and len(d['players'])==3: label+=' et charger 1 puissance'
            if race==9 and pi and newtype: label+=' · +3 connaissances'
            if race==16 and pi and newsector: label+=' · +2 crédits et 1 connaissance'
            if race==4 and pt==8: label+=' · +2 PV Gleens'
            credits=(0 if asteroid or gratuite else 2)+{35:3,36:6}.get(action,0)
            add(mode,label,credits,ore,price,qic,pw,formers=int(asteroid and action!=36 and not gratuite),construit=h,
                charge=int(bool(shared) and race==2 and pi and fleet and len(d['players'])==3),
                events={'mine':1,'mine Gaia':int(pt==8 and not shared),'étape':terra,
                        'nouveau secteur':int(newsector),'nouveau type':int(newtype and not shared)})
    if bonus_mine:
        add('Mine bonus','Renoncer')
        return results
    for h in cells:
        kind=h['planetType']
        xy=f"({h['q']}, {h['r']})"
        range_modes=[('Portée normale',0,0)]
        if p['boosterId']==2 and free(14): range_modes.append(('Booster',3,0))
        if fleet and race==4 and free(16): range_modes.append(('Gleens',2,0))
        if twilight and free(37): range_modes.append(('Crépuscule',3,1))
        for mode,extra,knowledge in range_modes:
            if kind==9 and not h['buildings'] and p['numAvailGaiaformers']:
                if mode=='Portée normale' and p['boosterId']==14 and free(15):
                    add('Booster Projet Gaia',xy,q=range_cost(h),formers=1)
                n=[6,6,6,4,3,3][p['research'][4]]
                add('Projet Gaia',xy+' · '+mode,k=knowledge,q=range_cost(h,extra),tokens=n,formers=1)
            if kind in {s['type'] for s in ships} and not any(s['type']==kind for s in visited):
                vp=7 if race==10 else 5
                if p.get('numShuttles',0) and p['score']>=vp and (race!=5 or p['race5brainstonePos']>0):
                    suffix=' · pierre-esprit vers Gaia' if race==5 else ''
                    add('Explorer',xy+f' · {mode} · {vp} PV'+suffix,k=knowledge,
                        q=range_cost(h,extra),tokens=int(race in (13,14)),pierre_gaia=race==5,
                        charge=(0,2,2,3)[next(len(v['playerIds']) for v in ships if v['type']==kind)])
    for group in federation_without_satellites(d,pid,distance):
        tiles={i for i,n in enumerate(board.get('availFedTokens',[])) if i and n}
        tiles.update(s['availFedTokenId'] for s in visited if s.get('availFedTokenId'))
        for tile in sorted(tiles):
            add('Alliance sans satellite',f'{group} · tuile {tile}',events={'alliance':1})
    for h,b in colonies:
        xy=f"({h['q']}, {h['r']})"
        if race==2 and any(str(u['playerId'])!=pid for u in h['buildings']): continue
        if b==4 and p['buildings']['5']:
            neighbor=any(distance(z,h)<=2 and any(str(u['playerId'])!=pid and u['buildingId']>=4 for u in z['buildings']) for z in cells)
            add('Amélioration','Comptoir '+xy,3 if neighbor else 6,2,construit=h,events={"comptoir":1})
            if 17 in types_visites and free(40):
                add('Comptoir via Rébellion',xy,o=1,power=3,construit=h,events={'comptoir':1})
        if b==5 and p['buildings']['6']:
            if twilight and free(39):
                tech_choices('Laboratoire via Crépuscule',xy,o=2,power=3,events={'laboratoire':1},construit=h)
            tech_choices('Laboratoire',xy,5,3,{'laboratoire':1},construit=h)
        if b==(6 if race==12 else 5) and not pi:
            if race==18: tech_choices('Institut',xy,6,4,{'académie ou institut':1},construit=h)
            else: add('Institut',xy+(' · tuile Alliance Gleens' if race==4 else ''),6,4,
                      construit=h,events={'académie ou institut':1,'alliance':int(race==4)})
        if b==(5 if race==12 else 6):
            for slot in ('7','8'):
                if p['buildings'][slot]: tech_choices('Académie',xy+' · '+slot,6,6,{'académie ou institut':1},construit=h)
        if special_ready and pi:
            if race==6 and b==4: add('Institut Ambas','Échanger avec la mine '+xy)
            if race==11 and b==6 and p['buildings']['5']:
                for track in pistes(d,pid) or [0]:
                    add('Institut Firaks',xy+' · comptoir · '+(TRACKS[track-1] if track else 'sans progression'),
                        track=track,construit=h,events={'comptoir':1,'recherche':int(bool(track))})
            if race==17 and sum(bool(u.get('hasRing')) for z in cells for u in z['buildings'] if str(u['playerId'])==pid)<6 and not any(u.get('hasRing') for u in h['buildings'] if str(u['playerId'])==pid):
                add('Institut Moweyds','Poser un anneau '+xy)
    if race==8 and pi and special_ready and sum(b==3 for _,b in owned)<6:
        for h in cells:
            if h['planetType']==0 and not any(u['buildingId']==3 for u in h['buildings']):
                add('Institut Ivits',f"Station ({h['q']}, {h['r']})",q=range_cost(h))
    if race==12 and special_ready:
        for track in pistes(d,pid):
            if p['research'][track]==min(p['research'][1:]):
                add('Bescods',TRACKS[track-1],track=track,events={'recherche':1})
    if race==15 and pi and special_ready and free(45) and tink in (2,3,5,6):
        add('Bricolage',{2:'Charger 4 puissance',3:'Gagner 1 QIC',5:'Gagner 3 connaissances',6:'Gagner 2 QIC'}[tink],charge=4 if tink==2 else 0)
    if not p['buildings']['8'] and not p['hasUsedAcademyAction']:
        add('Académie','Gagner 4 crédits' if race==10 else 'Gagner 1 QIC')
    for track in pistes(d,pid):
        add('Recherche',TRACKS[track-1],k=4,track=track,events={'recherche':1})
        if 15 in types_visites and free(41):
            add('Recherche via Éclipse',TRACKS[track-1],k=2,power=3,track=track,events={'recherche':1})
    if not fleet and free(10):
        tech_choices('Technologie QIC','Acquérir',q=4)
    if 17 in types_visites and free(34):
        tech_choices('Technologie via Rébellion','Acquérir',q=3)
    for index,pw,label in [(1,3,'Gagner 2 jetons I'),(2,4,'Gagner 2 minerais'),(3,4,'Gagner 7 crédits'),(4,4,'Gagner 2 connaissances'),(5,7,'Gagner 3 connaissances')]:
        if free(index):
            add('Puissance',label,power=pw)
    for tile in p['techs']:
        tid=tile['techId']
        if tid==9 and not tile.get('isCovered') and not tile['isActionUsed']:
            add('Action technologique','Charger 4 puissances',charge=4)
        if tid in (10,11,12) and not tile.get('isCovered') and not tile['isActionUsed']:
            reward=gains_technologie(tid,'action',metrics)
            add('Action technologique',' + '.join(f'{v} {u}' for u,v in reward.items()))
    for art in twilight.get('availArtifacts',[]):
        if art:
            effects={7:'3 PV + 1 PV par type colonisé', 10:'5 crédits et 2 minerais', 6:'3 PV par secteur extérieur colonisé'}
            add('Artefact',f'Crépuscule · {effects.get(art,art)}',tokens=6)
    if board['roundNum']==6:
        add('Passer','Dernière manche',events={'passage':1})
        return results
    for boost in board['availBoosters']:
        add('Passer',f'Booster {boost} · '+{7:'comptoirs',8:'laboratoires',9:'institut et académies'}.get(boost,''),events={'passage':1})
    return results

if __name__=='__main__':
    parser=ArgumentParser(description='Calculer les coups ou les réserves après paiement.')
    parser.add_argument('export')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--paiements',type=int,metavar='NUMERO')
    mode.add_argument('--conversions',action='store_true',help='Conversions libres depuis les réserves de l’export')
    args=parser.parse_args()
    data=json.loads(Path(args.export).read_text(encoding='utf8'))
    phase=data['gamestate']['name']
    libre=phase in ('statePlayerTurn','stateConvert','stateExtraMineBuild')
    joueur=data['players'][str(data['gamestate']['active_player'])]
    moteur=Conversions(joueur,bool(data['board']['config'].get('lostFleet')))
    if args.conversions:
        if not libre:
            parser.error('Les conversions libres du tour normal sont indisponibles dans cette phase')
        for chemin,etat in moteur.paiements((0,)*7):
            print((' → '.join(chemin) or 'Aucune conversion')+' · '+etat.description())
        raise SystemExit
    projections={}
    results=analyze(data,projections)
    coups=[(g,row) for g,rows in results.items() for row in rows]
    def options(group,row):
        projet=projections[group,row[0]]
        return moteur.paiements(projet['cout'],projet['vers_gaia'])
    if args.paiements is not None:
        if not libre or not 1<=args.paiements<=len(coups):
            parser.error('Numéro de coup ou phase incompatible')
        group,row=coups[args.paiements-1]
        print(group+' · '+row[0])
        for chemin,etat in options(group,row):
            print((' → '.join(chemin) or 'Direct')+' · '+etat.description())
        raise SystemExit
    print('# Projet Gaia · coup',data['notifications']['move_nbr'])
    print('\nLes soldes comparent les réserves juste après paiement, avant les effets du coup. Chaque numéro permet de consulter tous les paiements.\n')
    numero=0
    apercus={}
    for group,rows in results.items():
        print(f'## {group} ({len(rows)})\n\n| Choix | Coût principal | Préparation | N° | Soldes après paiement (exemples) |\n|---|---|---|---|---|')
        for row in rows:
            numero+=1
            detail=''
            if libre:
                projet=projections[group,row[0]]
                cle=(projet['cout'],projet['vers_gaia'])
                if cle not in apercus:
                    apercus[cle]=' / / '.join((' → '.join(p) or 'Direct')+' ⇒ '+e.description()
                        for p,e in islice(options(group,row),3))
                detail=apercus[cle]
            print('| '+' | '.join((*row,str(numero),detail))+' |')
        print()
