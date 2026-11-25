"""Régressions sur le coup témoin. Lancer python verifier.py."""
from pathlib import Path
import json
from analyse import analyze, distance

d = json.loads(Path(__file__).with_name('coup61.json').read_text())
r = analyze(d)
assert len(r['Laboratoire']) == 24
assert len(r['Recherche']) == 6
assert all(row[2] == 'direct' for row in r['Artefact'])
assert any(row[0]=='Glace (2, -1)' and row[2]=='direct' for row in r['Mine via le Crépuscule'])
assert all('Glace' not in row[0] and 'Gaia' not in row[0] for group in r if 'étape' in group for row in r[group])
assert all(row[0]!='Gagner 2 minerais' for row in r['Puissance'])
d['board']['usedActions'][37] = int(d['gamestate']['active_player'])
assert 'Mine via le Crépuscule' not in analyze(d)
print('Contrôles du coup témoin réussis.')
