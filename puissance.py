"""Transitions de puissance. Les jetons ordinaires et la pierre-esprit sont distincts."""
from dataclasses import dataclass, replace
from functools import lru_cache


@dataclass(frozen=True, order=True)
class Bols:
    gaia: int
    i: int
    ii: int
    iii: int
    pierre: int = -1  # -1 absente, 0 Gaia

    @classmethod
    def joueur(cls, joueur):
        return cls(*map(int, joueur['power']), int(joueur.get('race5brainstonePos', -1)))

    def appliquer(self, joueur):
        """Nouvel état BGA du joueur, sans modifier la position source."""
        return {**joueur, 'power': [self.gaia, self.i, self.ii, self.iii],
                'race5brainstonePos': self.pierre}

    def description(self):
        pierre = '' if self.pierre < 0 else ' · pierre ' + ('Gaia','I','II','III')[self.pierre]
        return f'bols I/II/III {self.i}/{self.ii}/{self.iii} · Gaia {self.gaia}' + pierre

    def charger(self, montant, priorite=False):
        if montant < 0:
            raise ValueError('Charge négative')
        reste = montant
        bols = [self.gaia, self.i, self.ii, self.iii]
        pierre = self.pierre
        for source in (1, 2):
            if priorite and pierre == source and reste:
                pierre += 1
                reste -= 1
            transfert = min(reste, bols[source])
            bols[source] -= transfert
            bols[source + 1] += transfert
            reste -= transfert
            if pierre == source and reste:
                pierre += 1
                reste -= 1
        return Bols(*bols, pierre), montant - reste

    def payer(self, puissance, jetons, multiplicateur):
        """Dépense III → I, puis défausse éventuelle parmi les bols."""
        for pierre in range(1 + int(self.pierre == 3 and puissance > 0)):
            cout = (max(0, puissance - 3*pierre) + multiplicateur-1)//multiplicateur
            if cout > self.iii:
                continue
            etat = replace(self, i=self.i+cout, iii=self.iii-cout,
                           pierre=1 if pierre else self.pierre)
            for i in range(min(etat.i, jetons)+1):
                for ii in range(min(etat.ii, jetons-i)+1):
                    iii = jetons-i-ii
                    if iii <= etat.iii:
                        yield replace(etat, i=etat.i-i, ii=etat.ii-ii, iii=etat.iii-iii)


def reactions(joueur, offre):
    depart = Bols.joueur(joueur)
    yield 'Décliner', depart, 0
    institut = joueur['raceId'] == 5 and not joueur['buildings']['9']
    for ordre in (('avant','après') if institut else ('',)):
        etat = replace(depart, i=depart.i+1) if ordre=='avant' else depart
        for arrivee, n in sorted({etat.charger(min(offre, joueur['score']+1), b) for b in (False, True)}):
            if n:
                if ordre=='après':
                    arrivee = replace(arrivee, i=arrivee.i+1)
                choix = f'Charger {n} pour {n-1} PV' + (f' · jeton I {ordre}' if ordre else '')
                yield choix, arrivee, n-1


def appliquer_reaction(joueur, offre, choix, bols):
    """Valide une décision et renvoie le joueur avec ses nouveaux bols et PV."""
    for nom, etat, prix in reactions(joueur, offre):
        if (nom, etat) == (choix, bols):
            return {**etat.appliquer(joueur), 'score': joueur['score'] - prix}
    raise ValueError('Réaction de puissance indisponible')


def revenus(depart, charges, nouveaux, directs=0):
    """Ordonne les lots indivisibles. Une priorité de pierre par décision BGA."""
    @lru_cache(None)
    def parcourir(etat, lots, priorite):
        if not lots:
            return {etat}
        fins = set()
        for index, (gain, quantite) in enumerate(lots):
            if index and lots[index]==lots[index-1]:
                continue
            suivant = replace(etat, i=etat.i+quantite) if gain else etat.charger(quantite, priorite)[0]
            fins.update(parcourir(suivant, lots[:index]+lots[index+1:], priorite))
        return fins
    lots = tuple(sorted([(False,n) for n in charges] + [(True,n) for n in nouveaux]))
    depart = replace(depart, iii=depart.iii+directs)
    return sorted(parcourir(depart,lots,False) | parcourir(depart,lots,True))


def charge_recherche(p, piste):
    if piste and p['research'][piste] == 2:
        return 3
    return 6 if piste == 5 and p['research'][5] == 4 else 0
