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
  décompte et bips, séries d'essais (par défaut **3 × 60 s** : ≥ 60 s pour la SampEn,
  Montesinos et al. 2018 ; moyenne de 3 à 5 essais, Ruhe et al. 2010).
- **Rangement** (convention v2.3) : `<dossier>/<groupe_temps>/<YO-dur>/<sujet>_<n>.csv`,
  numérotation reprise à la suite des essais existants (rien n'est écrasé).
- **Analyse** (BrainBloX Analysis v2.3) : descripteurs positionnels, dynamiques, spectraux,
  stochastiques (SDA, temps critiques par axe) et non linéaires (SampEn, DFA, RQA) ;
  import par fichiers ou dossiers avec reconnaissance sujet / essai / groupe / temps / condition ;
  vue « Sujets » (moyenne ± ET) ; onglet Réglages ; rapports PDF ; export Excel
  *Means / Trials / Settings* (colonnes en anglais).
- **Onglet Essentiel** (premier onglet de l'analyse) : 14 descripteurs, un ou deux par dimension
  (taille et direction, vitesse, fréquence, stochastique, complexité ; choix inspiré de l'ACP de
  Rocchi, Chiari & Cappello 2004), avec statokinésigramme et stabilogrammes ML / AP.
- **Vue Sujets** : bascule *Essais* (essais superposés) / *Moyenne* (ellipse 95 % moyenne avec
  axes et orientation moyens, centre moyen ± 1 ET ; amplitude d'oscillation = ET glissant 2 s,
  moyenne ± 1 ET entre essais — les déplacements bruts ne sont pas moyennés, car les essais ne
  sont pas synchronisés dans le temps).
- **Valeurs inhabituelles** : fichier de références (onglet Réglages, modèle fourni : `metric`,
  `mean`, `sd`, en option `eyes`, `surface`, `n`, `source`) ; cases orange / rouge au-delà de deux
  seuils de |z| (1,96 et 3 par défaut), z et référence en infobulle. Aucune norme n'est fournie.
- **Fenêtre de progression** pendant les traitements longs (dossiers, sujets, exports, rapports).
- **Comparaison** (fenêtre séparée) : 2 à 6 essais ou moyennes, statokinésigrammes superposés,
  diagramme d'un descripteur, tableau avec écart et rapport au premier élément.
- **Dossiers mémorisés** d'une session à l'autre (enregistrement, import, export, rapports).
- **Interface en français**, anglais au choix (onglet Réglages, relance immédiate).
- Lit aussi les anciens fichiers **BrainBLoX** (axe AP redressé comme dans la v2.3).

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

- Ré-échantillonnage **SWARII** à 25 Hz (par défaut), fenêtre 0,25 s (Audiffren & Contal, 2016) —
  la Wii Balance Board échantillonne de façon irrégulière (~60-65 mesures distinctes/s).
  L'interpolation linéaire reste disponible (onglet Réglages) ; elle redonne exactement les
  résultats de BrainBloX Analysis v2.3.
- Butterworth passe-bas d'ordre 4, 10 Hz, sans déphasage.

⚠️ SWARII modifie les résultats par rapport à l'interpolation linéaire de la v2.3 (fichiers
d'exemple BrainBLoX) : vitesses et longueurs de trajet −9 à −15 %, aire d'ellipse −4 à −7 %,
**SampEn sur incréments −50 à −55 %**. Ne comparer que des données traitées avec la même
méthode (elle est inscrite dans la feuille *Settings* de l'export).

## Références

- Quijoux F. et al. (2021). A review of center of pressure (COP) variables to quantify standing
  balance in elderly people. *Physiological Reports* 9:e15067. doi:10.14814/phy2.15067
- Audiffren J., Contal E. (2016). Preprocessing the Nintendo Wii Board Signal to Derive More
  Accurate Descriptors of Statokinesigrams. *Sensors* 16(8):1208. doi:10.3390/s16081208
- Montesinos L. et al. (2018). On the use of approximate entropy and sample entropy with
  centre of pressure time-series. *J NeuroEng Rehabil* 15. doi:10.1186/s12984-018-0465-9
- Ruhe A., Fejer R., Walker B. (2010). The test-retest reliability of centre of pressure measures
  in bipedal static task conditions – a systematic review. *Gait & Posture* 32(4):436-445.
- Rocchi L., Chiari L., Cappello A. (2004). Feature selection of stabilometric parameters based on
  principal component analysis. *Med Biol Eng Comput* 42(1):71-79. doi:10.1007/BF02351013
- Appairage Bluetooth : logique reprise de l'émulateur Dolphin (`WiimoteReal/IOWin.cpp`).
- Protocole de la planche : wiibrew.org.

## Développement

```
pip install -r requirements.txt
python opensway.py
```

`acquisition/` (planche, simulateur, lecture en tâche de fond) · `core/` (format, SWARII,
analyses v2.3, traductions) · `gui/` (interface Tkinter) · `tests/`.
Chaque push sur `main` compile `OpenSway.exe` (GitHub Actions) ; un tag `vX.Y` publie une Release.
