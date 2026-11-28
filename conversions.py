"""Conversions libres du tour normal et soldes distincts après paiement."""
from collections import deque
from dataclasses import dataclass, replace
from puissance import Bols


@dataclass(frozen=True)
class Reserve:
    credits: int
    minerai: int
    connaissance: int
    qic: int
    bols: Bols
    gaiaformeurs: int
    excedent: int = 0  # utilisable uniquement dans le même lot de conversions

    @classmethod
    def joueur(cls, p):
        return cls(p['gold'],p['ore'],p['knowledge'],p['qic'],Bols.joueur(p),p['numAvailGaiaformers'])

    def description(self):
        return (f'{self.credits} cr, {self.minerai} min, {self.connaissance} conn, '
                f'{self.qic} QIC · {self.bols.description()} · {self.gaiaformeurs} gaiaformeur(s) disponible(s)')

    def changer(self, **delta):
        plafonds={'credits':30,'minerai':15,'connaissance':15}
        valeurs={k:getattr(self,k)+v for k,v in delta.items()}
        return replace(self,**{k:min(n,plafonds.get(k,n)) for k,n in valeurs.items()})


class Conversions:
    def __init__(self,p,flotte):
        self.depart=Reserve.joueur(p)
        self.race=p['raceId']
        self.institut=not int(p['buildings']['9'])
        self.qic_autorise=self.race!=4 or not p['buildings']['8']
        self.mult=2 if self.race==13 and self.institut else 1
        self.xenos=self.race==3 and flotte

    def transitions(self,s):
        b=s.bols
        if b.ii>=2:
            yield 'sacrifier en bol II',replace(s,bols=replace(b,ii=b.ii-2,iii=b.iii+1,gaia=b.gaia+int(self.race==14)))
        if b.ii and b.pierre==2:
            yield 'sacrifier la pierre-esprit en bol II',replace(s,bols=replace(b,ii=b.ii-1,iii=b.iii+1,pierre=-1))
            yield 'sacrifier pour charger la pierre-esprit',replace(s,bols=replace(b,ii=b.ii-1,pierre=3))
        if s.minerai:
            yield '1 minerai → 1 crédit',s.changer(minerai=-1,credits=1)
            yield '1 minerai → 1 jeton I',replace(s,minerai=s.minerai-1,bols=replace(b,i=b.i+1))
            if self.xenos:
                yield '1 minerai → 1 jeton III',replace(s,minerai=s.minerai-1,bols=replace(b,iii=b.iii+1))
        if s.connaissance:
            yield '1 connaissance → 1 crédit',s.changer(connaissance=-1,credits=1)
        if s.qic:
            yield '1 QIC → 1 minerai',s.changer(qic=-1,minerai=1)
        if self.race==10 and s.gaiaformeurs:
            yield 'gaiaformeur vers Gaia pour 1 QIC',s.changer(gaiaformeurs=-1,qic=1)
        if self.race==13 and b.iii:
            yield 'III vers Gaia pour 1 connaissance',replace(s.changer(connaissance=1),bols=replace(b,iii=b.iii-1,gaia=b.gaia+1))
        for res,prix,nom in [('credits',1,'crédit'),('minerai',3,'minerai'),('connaissance',4,'connaissance'),('qic',4,'QIC')]:
            if res=='qic' and not self.qic_autorise:
                continue
            if self.race==7 and self.institut and res!='credits' and s.credits>=prix:
                yield f'{prix} crédits → 1 {nom}',s.changer(credits=-prix,**{res:1})
            for pierre in range(1+int(b.pierre==3 and s.excedent<prix)):
                reste=max(0,prix-s.excedent-3*pierre)
                jetons=(reste+self.mult-1)//self.mult
                if jetons>b.iii:
                    continue
                solde=s.excedent+jetons*self.mult+3*pierre-prix
                bols=replace(b,iii=b.iii-jetons,i=b.i+jetons,pierre=1 if pierre else b.pierre)
                source='pierre-esprit et jetons III' if pierre else 'puissance'
                yield f'{prix} {source} → 1 {nom}',replace(s.changer(**{res:1}),bols=bols,excedent=solde)

    def issues(self,s,cout,vers_gaia=False):
        c,o,k,q,pw,tokens,g=cout
        if s.credits<c or s.minerai<o or s.connaissance<k or s.qic<q or s.gaiaformeurs<g:
            return
        for pierre in range(1+int(tokens>0 and s.bols.pierre in (1,2,3))):
            b=replace(s.bols,pierre=(0 if vers_gaia else -1)) if pierre else s.bols
            for fin in b.payer(pw,tokens-pierre,self.mult):
                if vers_gaia:
                    fin=replace(fin,gaia=fin.gaia+tokens-pierre)
                yield Reserve(s.credits-c,s.minerai-o,s.connaissance-k,s.qic-q,fin,s.gaiaformeurs-g)

    def possible(self,s,cout):
        # Majorants optimistes : une même ressource peut aider plusieurs tests.
        c,o,k,q,pw,tokens,g=cout
        b=s.bols
        formers=s.gaiaformeurs-g
        if formers<0 or max(c-30,o-15,k-15)>0:
            return False
        qic=s.qic+(formers if self.race==10 else 0)
        potentiel=(b.iii+b.ii//2)*self.mult+s.excedent
        if b.pierre==3 or (b.pierre==2 and b.ii):
            potentiel+=3
        if self.xenos:
            potentiel+=s.minerai+qic
        if potentiel<pw:
            return False
        monnaie=potentiel-pw
        if self.race==7 and self.institut:
            monnaie+=s.credits+s.connaissance+s.minerai+qic
        if q>qic+(monnaie//4 if self.qic_autorise else 0):
            return False
        if o>s.minerai+max(0,qic-q)+monnaie//3:
            return False
        if k>s.connaissance+monnaie//4+(b.iii+b.ii//2 if self.race==13 else 0):
            return False
        ressources=s.minerai+qic+monnaie//3
        if tokens>b.i+b.ii+b.iii+int(b.pierre>0)+ressources:
            return False
        return c<=s.credits+s.minerai+qic+s.connaissance+potentiel

    def parcours(self,cout,vers_gaia=False):
        """Un chemin le plus court par réserve atteinte, sans seuil de profondeur."""
        file=deque([(self.depart,())])
        vus={self.depart}
        while file:
            s,chemin=file.popleft()
            if not self.possible(s,cout):
                continue
            for fin in self.issues(s,cout,vers_gaia):
                yield chemin,s,fin
            for nom,suivant in self.transitions(s):
                if suivant not in vus:
                    vus.add(suivant)
                    file.append((suivant,chemin+(nom,)))

    def paiements(self,cout,vers_gaia=False):
        vus=set()
        for chemin,_,fin in self.parcours(cout,vers_gaia):
            if fin not in vus:
                vus.add(fin)
                yield chemin,fin

