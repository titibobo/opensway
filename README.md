# OpenSway

Stabilométrie sur **Wii Balance Board** : connexion, enregistrement et analyse dans un seul programme.

Développé par Thibault Marin, DO PhD — Département Recherche, **École Supérieure d'Ostéopathie (ESO Paris)**.
Successeur de *BrainBloX Analysis* : BrainBLoX et WiiBalanceWalker ne sont plus nécessaires.

## Pour les utilisateurs

1. Télécharger `OpenSway.exe` (onglet *Releases*, ou *Actions → dernier build → OpenSway-windows*).
2. Le lancer (Windows : « Informations complémentaires → Exécuter quand même » au premier lancement).
3. Onglet **Acquisition** → *Connecter*. Si la planche n'est pas trouvée, appuyer sur le bouton
   rouge **SYNC** (sous le capot des piles) quand le programme le demande. Une fois appairée sur
   un PC, le bouton **POWER** suffit en général les fois suivantes.
4. **Tare** planche vide, renseigner le sujet et les conditions, puis **Démarrer**.

Le **simulateur** permet de préparer un TP ou de découvrir le logiciel sans planche
(signal artificiel : ne pas l'utiliser comme donnée).

## Fonctions

- **Acquisition** : appairage Bluetooth automatique (Windows), tare, CoP en temps réel,
  décompte et bips de début/fin, séries de *n* essais avec pause ou validation manuelle.
- **Conditions** : yeux ouverts/fermés (YO/YF), sol dur/mousse, note libre — inscrites dans
  le nom et l'en-tête du fichier.
- **Analyse** : descripteurs positionnels, dynamiques, fréquentiels et stochastiques
  (Quijoux et al., 2021), rapport PDF, export Excel.
- **Moyennage** (optionnel, à l'export Excel) : moyennes et écarts-types par sujet × yeux ×
  surface, quotient de Romberg (YF/YO × 100).
- **Mode démo pédagogique** : affichage grand format, traînée réglable, mesures A/B superposées
  et comparées.
- Lit aussi les anciens fichiers **BrainBLoX** (axe AP redressé comme dans BrainBloX Analysis v2.0).

## Format de fichier OpenSway v1

En-tête `# clé : valeur`, puis 8 colonnes séparées par des espaces, **données brutes**
(rythme natif de la planche, non ré-échantillonné) :

```
# format   : OpenSway v1
# sujet    : S012
# yeux     : YF
# surface  : dur
# essai    : 2
# axes     : ML+ = droite, AP+ = avant
# colonnes : t_ms TL_kg TR_kg BL_kg BR_kg cop_ml_cm cop_ap_cm total_kg
```

## Pré-traitement

- Ré-échantillonnage **SWARII** à 25 Hz, fenêtre 0,25 s (Audiffren & Contal, 2016) —
  la Wii Balance Board échantillonne de façon irrégulière (~60-65 mesures distinctes/s).
  L'interpolation linéaire de la v2.0 reste disponible (paramètre *Resampling*) ; elle redonne
  exactement les résultats de BrainBloX Analysis v2.0.
- Butterworth passe-bas d'ordre 4, 10 Hz, sans déphasage.

⚠️ SWARII modifie surtout les descripteurs de vitesse et de longueur de trajet (−10 à −15 % sur
les fichiers d'exemple) : ne comparer que des données traitées avec la même méthode.

## Références

- Quijoux F. et al. (2021). A review of center of pressure (COP) variables to quantify standing
  balance in elderly people. *Physiological Reports* 9:e15067. doi:10.14814/phy2.15067
- Audiffren J., Contal E. (2016). Preprocessing the Nintendo Wii Board Signal to Derive More
  Accurate Descriptors of Statokinesigrams. *Sensors* 16(8):1208. doi:10.3390/s16081208
- Appairage Bluetooth : logique reprise de l'émulateur Dolphin (`WiimoteReal/IOWin.cpp`).
- Protocole de la planche : wiibrew.org.

## Développement

```
pip install -r requirements.txt
python opensway.py
```

`acquisition/` (planche, simulateur, lecture en tâche de fond) · `core/` (format, SWARII,
analyses) · `gui/` (interface Tkinter) · `tests/`.
Chaque push sur `main` compile `OpenSway.exe` (GitHub Actions) ; un tag `vX.Y` publie une Release.
