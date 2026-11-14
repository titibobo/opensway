"""
Langue de l'interface (français par défaut, anglais en option).

- tr("English text")       -> texte traduit (ou l'original en anglais)
- metric_label(label_en)   -> libellé de descripteur à largeur fixe (alignement)
- metric_tooltip(label_en) -> infobulle du descripteur

Les libellés anglais de params.GUI_METRIC_LABELS restent les identifiants internes ;
les noms de colonnes exportés ne sont jamais traduits.
"""
from __future__ import annotations

LANGUAGES = ("fr", "en")
_lang = "fr"


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGUAGES else "fr"


def get_language() -> str:
    return _lang


def tr(text: str) -> str:
    if _lang == "en":
        return text
    return FR.get(text, text)


# -----------------------------------------------------------------------------
# Libellés de descripteurs : même gabarit que les libellés anglais
# (nom calé à gauche, unité entre parenthèses calée à droite, 26 caractères)
# -----------------------------------------------------------------------------
_W = 25

def _fw(name: str, unit: str) -> str:
    u = f"({unit})" if unit else ""
    return f"{name}{' ' * max(1, _W - len(name) - len(u))}{u} "


_FR_METRICS = {
    # Positionnels
    "ML mean position     (cm) ": ("Position moy. ML",     "cm"),
    "AP mean position     (cm) ": ("Position moy. AP",     "cm"),
    "ML RMS               (cm) ": ("RMS ML",               "cm"),
    "AP RMS               (cm) ": ("RMS AP",               "cm"),
    "Global RMS radius    (cm) ": ("Rayon RMS global",     "cm"),
    "Planar deviation     (cm) ": ("Déviation planaire",   "cm"),
    "ML mean distance     (cm) ": ("Distance moy. ML",     "cm"),
    "AP mean distance     (cm) ": ("Distance moy. AP",     "cm"),
    "Mean radius          (cm) ": ("Rayon moyen",          "cm"),
    "ML maximal distance  (cm) ": ("Distance max. ML",     "cm"),
    "AP maximal distance  (cm) ": ("Distance max. AP",     "cm"),
    "Maximal radius       (cm) ": ("Rayon maximal",        "cm"),
    "ML range             (cm) ": ("Amplitude ML",         "cm"),
    "AP range             (cm) ": ("Amplitude AP",         "cm"),
    "AP-ML range          (cm) ": ("Amplitude AP-ML",      "cm"),
    "Range ratio           (-) ": ("Rapport amplitudes",   "-"),
    "Sway direct° coeff.   (-) ": ("Coeff. dir. oscill.",  "-"),
    "95% ellipse area    (cm²) ": ("Aire ellipse 95 %",    "cm²"),
    "Princ. sway direct°   (°) ": ("Dir. princ. oscill.",  "°"),
    # Dynamiques
    "ML path length       (cm) ": ("Longueur trajet ML",   "cm"),
    "AP path length       (cm) ": ("Longueur trajet AP",   "cm"),
    "Global path length   (cm) ": ("Longueur trajet",      "cm"),
    "LFS                (cm⁻¹) ": ("LFS",                  "cm⁻¹"),
    "ML mean velocity   (cm/s) ": ("Vitesse moy. ML",      "cm/s"),
    "AP mean velocity   (cm/s) ": ("Vitesse moy. AP",      "cm/s"),
    "Global mean vel.   (cm/s) ": ("Vitesse moy. glob.",   "cm/s"),
    "ML 0-crossings set    (-) ": ("Passages à 0 ML",      "-"),
    "AP 0-crossings set    (-) ": ("Passages à 0 AP",      "-"),
    "ML mean frequency    (Hz) ": ("Fréquence moy. ML",    "Hz"),
    "AP mean frequency    (Hz) ": ("Fréquence moy. AP",    "Hz"),
    "Global mean freq.    (Hz) ": ("Fréq. moy. globale",   "Hz"),
    "VFY                   (-) ": ("VFY",                  "-"),
    "Area per second   (cm²/s) ": ("Aire par seconde",     "cm²/s"),
    "ML phase plane            ": ("Plan de phase ML",     ""),
    "AP phase plane            ": ("Plan de phase AP",     ""),
    "Fractal dimension     (-) ": ("Dimension fractale",   "-"),
    "ML peak pos. vel.  (cm/s) ": ("Pic vit. + ML",        "cm/s"),
    "ML peak neg. vel.  (cm/s) ": ("Pic vit. - ML",        "cm/s"),
    "ML mean peak vel.  (cm/s) ": ("Pic vit. moy. ML",     "cm/s"),
    "AP peak pos. vel.  (cm/s) ": ("Pic vit. + AP",        "cm/s"),
    "AP peak neg. vel.  (cm/s) ": ("Pic vit. - AP",        "cm/s"),
    "AP mean peak vel.  (cm/s) ": ("Pic vit. moy. AP",     "cm/s"),
    "Mean SD peaks dist.  (cm) ": ("ET dist. entre pics",  "cm"),
    "Mean peaks' interval  (s) ": ("Intervalle des pics",  "s"),
    # Spectraux
    "ML total power      (cm²) ": ("Puissance tot. ML",    "cm²"),
    "AP total power      (cm²) ": ("Puissance tot. AP",    "cm²"),
    "ML 50% power freq.   (Hz) ": ("Fréq. 50% puiss. ML",  "Hz"),
    "AP 50% power freq.   (Hz) ": ("Fréq. 50% puiss. AP",  "Hz"),
    "ML 95% power freq.   (Hz) ": ("Fréq. 95% puiss. ML",  "Hz"),
    "AP 95% power freq.   (Hz) ": ("Fréq. 95% puiss. AP",  "Hz"),
    "ML power mode        (Hz) ": ("Mode de puiss. ML",    "Hz"),
    "AP power mode        (Hz) ": ("Mode de puiss. AP",    "Hz"),
    "ML centroidal freq.  (Hz) ": ("Fréq. centroïde ML",   "Hz"),
    "AP centroidal freq.  (Hz) ": ("Fréq. centroïde AP",   "Hz"),
    "ML freq. dispersion   (-) ": ("Dispersion fréq. ML",  "-"),
    "AP freq. dispersion   (-) ": ("Dispersion fréq. AP",  "-"),
    "ML [0-0.5] Hz       (cm²) ": ("ML [0-0.5] Hz",        "cm²"),
    "AP [0-0.5] Hz       (cm²) ": ("AP [0-0.5] Hz",        "cm²"),
    "ML [0.5–2] Hz       (cm²) ": ("ML [0.5–2] Hz",        "cm²"),
    "AP [0.5–2] Hz       (cm²) ": ("AP [0.5–2] Hz",        "cm²"),
    "ML  [2–5]  Hz       (cm²) ": ("ML  [2–5]  Hz",        "cm²"),
    "AP  [2–5]  Hz       (cm²) ": ("AP  [2–5]  Hz",        "cm²"),
    "ML freq. quotient     (-) ": ("Quotient fréq. ML",    "-"),
    "AP freq. quotient     (-) ": ("Quotient fréq. AP",    "-"),
    # Stochastiques
    "ML ST Hurst exp.      (-) ": ("Hurst CT ML",          "-"),
    "AP ST Hurst exp.      (-) ": ("Hurst CT AP",          "-"),
    "ML LT Hurst exp.      (-) ": ("Hurst LT ML",          "-"),
    "AP LT Hurst exp.      (-) ": ("Hurst LT AP",          "-"),
    "ML ST diffus. coeff.  (-) ": ("Coeff. diff. CT ML",   "-"),
    "AP ST diffus. coeff.  (-) ": ("Coeff. diff. CT AP",   "-"),
    "ML LT diffus. coeff.  (-) ": ("Coeff. diff. LT ML",   "-"),
    "AP LT diffus. coeff.  (-) ": ("Coeff. diff. LT AP",   "-"),
    "ML crit. time Tc      (s) ": ("Temps crit. Tc ML",    "s"),
    "AP crit. time Tc      (s) ": ("Temps crit. Tc AP",    "s"),
    "ML MSD at Tc        (cm²) ": ("MSD à Tc ML",          "cm²"),
    "AP MSD at Tc        (cm²) ": ("MSD à Tc AP",          "cm²"),
    # Non linéaires
    "ML sample entropy     (-) ": ("SampEn ML",            "-"),
    "AP sample entropy     (-) ": ("SampEn AP",            "-"),
    "ML DFA α short-term   (-) ": ("DFA α court t. ML",    "-"),
    "AP DFA α short-term   (-) ": ("DFA α court t. AP",    "-"),
    "ML DFA α long-term    (-) ": ("DFA α long t. ML",     "-"),
    "AP DFA α long-term    (-) ": ("DFA α long t. AP",     "-"),
    "ML RQA recurrence     (%) ": ("RQA récurrence ML",    "%"),
    "AP RQA recurrence     (%) ": ("RQA récurrence AP",    "%"),
    "ML RQA determinism    (%) ": ("RQA déterminisme ML",  "%"),
    "AP RQA determinism    (%) ": ("RQA déterminisme AP",  "%"),
    "ML RQA max. line    (pts) ": ("RQA ligne max. ML",    "pts"),
    "AP RQA max. line    (pts) ": ("RQA ligne max. AP",    "pts"),
    "ML RQA line entropy   (-) ": ("RQA entropie ML",      "-"),
    "AP RQA line entropy   (-) ": ("RQA entropie AP",      "-"),
    "ML embedding dim.     (-) ": ("Dim. plongement ML",   "-"),
    "AP embedding dim.     (-) ": ("Dim. plongement AP",   "-"),
    "ML embedding delay    (s) ": ("Délai plongement ML",  "s"),
    "AP embedding delay    (s) ": ("Délai plongement AP",  "s"),
    # Divers
    "Duration              (s) ": ("Durée",                "s"),
}


def metric_label(label_en: str) -> str:
    if _lang == "en" or label_en not in _FR_METRICS:
        return label_en
    return _fw(*_FR_METRICS[label_en])


def metric_short(label_en: str) -> str:
    """Libellé sans espaces de remplissage (tableaux, légendes)."""
    return " ".join(metric_label(label_en).split())


def metric_tooltip(label_en: str) -> str:
    from .params import METRIC_TOOLTIPS
    if _lang == "fr" and label_en in FR_TOOLTIPS:
        return FR_TOOLTIPS[label_en]
    return METRIC_TOOLTIPS.get(label_en, "")


# -----------------------------------------------------------------------------
# Infobulles des descripteurs (français)
# -----------------------------------------------------------------------------
FR_TOOLTIPS = {
    "ML mean position     (cm) ": "Position ML moyenne (cm, signal filtré non centré) ± écart-type.\nDépend du placement des pieds sur la planche.",
    "AP mean position     (cm) ": "Position AP moyenne (cm, + = avant, signal filtré non centré) ± écart-type.\nDépend du placement des pieds sur la planche.",
    "ML RMS               (cm) ": "Moyenne quadratique du déplacement ML autour du centre (cm).",
    "AP RMS               (cm) ": "Moyenne quadratique du déplacement AP autour du centre (cm).",
    "Global RMS radius    (cm) ": "Moyenne quadratique de la distance radiale √(ML² + AP²) (cm). Dispersion globale.",
    "Planar deviation     (cm) ": "Dispersion 2D calculée à partir des écarts-types ML et AP (cm).",
    "ML mean distance     (cm) ": "Distance ML absolue moyenne au centre (cm).",
    "AP mean distance     (cm) ": "Distance AP absolue moyenne au centre (cm).",
    "Mean radius          (cm) ": "Distance radiale moyenne au centre (cm).",
    "ML maximal distance  (cm) ": "Distance ML absolue maximale au centre (cm).",
    "AP maximal distance  (cm) ": "Distance AP absolue maximale au centre (cm).",
    "Maximal radius       (cm) ": "Distance radiale maximale au centre (cm).",
    "ML range             (cm) ": "Amplitude ML crête à crête (max - min) (cm).",
    "AP range             (cm) ": "Amplitude AP crête à crête (max - min) (cm).",
    "AP-ML range          (cm) ": "Plus grande distance 2D entre deux points de l'enveloppe convexe (cm).",
    "Range ratio           (-) ": "Rapport des amplitudes : amplitude ML / amplitude AP (sans unité).",
    "Sway direct° coeff.   (-) ": "Coefficient de direction des oscillations : covariance ML-AP normalisée par les RMS (sans unité).",
    "95% ellipse area    (cm²) ": "Aire de l'ellipse de confiance à 95 % (cm²), issue de la matrice de covariance.",
    "Princ. sway direct°   (°) ": "Direction principale des oscillations (°), d'après le vecteur propre principal.",
    "ML path length       (cm) ": "Somme des déplacements ML absolus (cm). Dépend de la durée.",
    "AP path length       (cm) ": "Somme des déplacements AP absolus (cm). Dépend de la durée.",
    "Global path length   (cm) ": "Somme des déplacements 2D point à point (cm). Dépend de la durée.",
    "LFS                (cm⁻¹) ": "Longueur en fonction de la surface : longueur de trajet / aire de l'ellipse 95 % (cm⁻¹).",
    "ML mean velocity   (cm/s) ": "Vitesse ML absolue moyenne (cm/s) ± écart-type.",
    "AP mean velocity   (cm/s) ": "Vitesse AP absolue moyenne (cm/s) ± écart-type.",
    "Global mean vel.   (cm/s) ": "Norme moyenne de la vitesse 2D (cm/s) ± écart-type.",
    "ML 0-crossings set    (-) ": "Nombre de changements de signe de la vitesse ML (sans unité).",
    "AP 0-crossings set    (-) ": "Nombre de changements de signe de la vitesse AP (sans unité).",
    "ML mean frequency    (Hz) ": "Fréquence temporelle : vitesse ML moyenne / distance ML moyenne (Hz).",
    "AP mean frequency    (Hz) ": "Fréquence temporelle : vitesse AP moyenne / distance AP moyenne (Hz).",
    "Global mean freq.    (Hz) ": "Fréquence temporelle : vitesse globale moyenne / distance radiale moyenne (Hz).",
    "VFY                   (-) ": "VFY (cm.s⁻²) : variance de la norme de la vitesse / position AP moyenne (non centrée).\nDépend du placement des pieds ; exclu par Quijoux et al. pour erreur de mesure.",
    "Area per second   (cm²/s) ": "Aire balayée par seconde (cm²/s), somme des aires des triangles successifs.",
    "ML phase plane            ": "Indice du plan de phase ML : ET(position) + ET(vitesse) (sans unité).",
    "AP phase plane            ": "Indice du plan de phase AP : ET(position) + ET(vitesse) (sans unité).",
    "Fractal dimension     (-) ": "Dimension fractale : log(N) / log(N.d/L), N échantillons, L longueur de trajet,\nd diamètre du cercle de même aire que l'ellipse 95 % (Quijoux et al.).",
    "ML peak pos. vel.  (cm/s) ": "Moyenne des pics de vitesse ML positifs, par segment de signe constant (cm/s).",
    "ML peak neg. vel.  (cm/s) ": "Moyenne des pics de vitesse ML négatifs, par segment de signe constant (cm/s).",
    "ML mean peak vel.  (cm/s) ": "Moyenne des pics de vitesse ML en valeur absolue (cm/s).",
    "AP peak pos. vel.  (cm/s) ": "Moyenne des pics de vitesse AP positifs, par segment de signe constant (cm/s).",
    "AP peak neg. vel.  (cm/s) ": "Moyenne des pics de vitesse AP négatifs, par segment de signe constant (cm/s).",
    "AP mean peak vel.  (cm/s) ": "Moyenne des pics de vitesse AP en valeur absolue (cm/s).",
    "Mean SD peaks dist.  (cm) ": "Écart-type des distances entre pics successifs de la distance radiale (cm).",
    "Mean peaks' interval  (s) ": "Intervalle de temps moyen entre pics de la distance radiale (s).",
    "ML total power      (cm²) ": "Puissance spectrale totale ML (aire sous la DSP, cm²).",
    "AP total power      (cm²) ": "Puissance spectrale totale AP (aire sous la DSP, cm²).",
    "ML 50% power freq.   (Hz) ": "Fréquence sous laquelle se trouve 50 % de la puissance ML (fréquence médiane).",
    "AP 50% power freq.   (Hz) ": "Fréquence sous laquelle se trouve 50 % de la puissance AP (fréquence médiane).",
    "ML 95% power freq.   (Hz) ": "Fréquence sous laquelle se trouve 95 % de la puissance ML.",
    "AP 95% power freq.   (Hz) ": "Fréquence sous laquelle se trouve 95 % de la puissance AP.",
    "ML power mode        (Hz) ": "Fréquence du maximum de la DSP ML (fréquence dominante).",
    "AP power mode        (Hz) ": "Fréquence du maximum de la DSP AP (fréquence dominante).",
    "ML centroidal freq.  (Hz) ": "Centroïde spectral ML : premier moment / puissance totale (Hz).",
    "AP centroidal freq.  (Hz) ": "Centroïde spectral AP : premier moment / puissance totale (Hz).",
    "ML freq. dispersion   (-) ": "Dispersion fréquentielle ML, d'après les moments spectraux (sans unité).",
    "AP freq. dispersion   (-) ": "Dispersion fréquentielle AP, d'après les moments spectraux (sans unité).",
    "ML [0-0.5] Hz       (cm²) ": "Énergie ML entre 0 et 0,5 Hz (cm²).",
    "AP [0-0.5] Hz       (cm²) ": "Énergie AP entre 0 et 0,5 Hz (cm²).",
    "ML [0.5–2] Hz       (cm²) ": "Énergie ML entre 0,5 et 2 Hz (cm²).",
    "AP [0.5–2] Hz       (cm²) ": "Énergie AP entre 0,5 et 2 Hz (cm²).",
    "ML  [2–5]  Hz       (cm²) ": "Énergie ML entre 2 et 5 Hz (cm²).",
    "AP  [2–5]  Hz       (cm²) ": "Énergie AP entre 2 et 5 Hz (cm²).",
    "ML freq. quotient     (-) ": "Quotient fréquentiel ML : énergie(2-5 Hz) / [énergie(0-0,5) + énergie(0,5-2)].",
    "AP freq. quotient     (-) ": "Quotient fréquentiel AP : énergie(2-5 Hz) / [énergie(0-0,5) + énergie(0,5-2)].",
    "ML ST Hurst exp.      (-) ": "Exposant de Hurst court terme (ML), analyse de diffusion du stabilogramme.\nMSD(Δt) = D.Δt^(2H), ajustements log-log sur [1/fs ; Tc] et [Tc ; T/3],\nrupture cherchée dans [0,3 ; 2,5] s (Réglages avancés).",
    "AP ST Hurst exp.      (-) ": "Exposant de Hurst court terme (AP), analyse de diffusion du stabilogramme.",
    "ML LT Hurst exp.      (-) ": "Exposant de Hurst long terme (ML), analyse de diffusion du stabilogramme.",
    "AP LT Hurst exp.      (-) ": "Exposant de Hurst long terme (AP), analyse de diffusion du stabilogramme.",
    "ML ST diffus. coeff.  (-) ": "Coefficient de diffusion court terme D = exp(ordonnée à l'origine) (cm².s^-2H).",
    "AP ST diffus. coeff.  (-) ": "Coefficient de diffusion court terme D = exp(ordonnée à l'origine) (cm².s^-2H).",
    "ML LT diffus. coeff.  (-) ": "Coefficient de diffusion long terme D = exp(ordonnée à l'origine) (cm².s^-2H).",
    "AP LT diffus. coeff.  (-) ": "Coefficient de diffusion long terme D = exp(ordonnée à l'origine) (cm².s^-2H).",
    "ML crit. time Tc      (s) ": "Temps critique Tc (s), ML : intersection des droites court et long terme,\nborné à [1/fs ; T/3].",
    "AP crit. time Tc      (s) ": "Temps critique Tc (s), AP : intersection des droites court et long terme,\nborné à [1/fs ; T/3].",
    "ML MSD at Tc        (cm²) ": "Déplacement quadratique moyen au temps critique, ML (cm²).",
    "AP MSD at Tc        (cm²) ": "Déplacement quadratique moyen au temps critique, AP (cm²).",
    "ML sample entropy     (-) ": "Entropie d'échantillon SampEn(m, r) des incréments du CoP ML par défaut\n(Richman & Moorman, 2000). Plus faible = plus régulier.\nDépend fortement de m, r, N et fs (Réglages avancés).",
    "AP sample entropy     (-) ": "Entropie d'échantillon SampEn(m, r) des incréments du CoP AP par défaut\n(Richman & Moorman, 2000). Plus faible = plus régulier.\nDépend fortement de m, r, N et fs (Réglages avancés).",
    "ML DFA α short-term   (-) ": "Exposant α de la DFA (positions ML), fenêtres de 4 échantillons au point de\ntransition (1 s par défaut). α ≈ 0,5 bruit non corrélé, 1 = 1/f, 1,5 = brownien (Peng et al., 1994).",
    "AP DFA α short-term   (-) ": "Exposant α de la DFA (positions AP), fenêtres de 4 échantillons au point de\ntransition (1 s par défaut). α ≈ 0,5 bruit non corrélé, 1 = 1/f, 1,5 = brownien (Peng et al., 1994).",
    "ML DFA α long-term    (-) ": "Exposant α de la DFA (positions ML), fenêtres du point de transition à N/4.\nInstable sur les enregistrements courts (30 s).",
    "AP DFA α long-term    (-) ": "Exposant α de la DFA (positions AP), fenêtres du point de transition à N/4.\nInstable sur les enregistrements courts (30 s).",
    "ML RQA recurrence     (%) ": "Taux de récurrence RQA (%), ML. Égal au taux cible (5 %) en mode « taux fixe » ;\nn'a de sens qu'en mode « rayon fixe » (Réglages avancés).",
    "AP RQA recurrence     (%) ": "Taux de récurrence RQA (%), AP. Égal au taux cible (5 %) en mode « taux fixe » ;\nn'a de sens qu'en mode « rayon fixe » (Réglages avancés).",
    "ML RQA determinism    (%) ": "Déterminisme RQA (%), ML : part des points récurrents formant des diagonales (≥ 2 points).\nRayon : taux de récurrence fixe (5 %) ou rayon fixe ; fenêtre de Theiler (m-1).τ.",
    "AP RQA determinism    (%) ": "Déterminisme RQA (%), AP : part des points récurrents formant des diagonales (≥ 2 points).\nRayon : taux de récurrence fixe (5 %) ou rayon fixe ; fenêtre de Theiler (m-1).τ.",
    "ML RQA max. line    (pts) ": "Plus longue diagonale RQA (points), ML. Liée à la stabilité des trajectoires récurrentes.",
    "AP RQA max. line    (pts) ": "Plus longue diagonale RQA (points), AP. Liée à la stabilité des trajectoires récurrentes.",
    "ML RQA line entropy   (-) ": "Entropie de Shannon de la distribution des longueurs de diagonales, ML\n(complexité de la structure déterministe).",
    "AP RQA line entropy   (-) ": "Entropie de Shannon de la distribution des longueurs de diagonales, AP\n(complexité de la structure déterministe).",
    "ML embedding dim.     (-) ": "Dimension de plongement m de la RQA (ML) : faux plus proches voisins < 1 % (Kennel et al., 1992).",
    "AP embedding dim.     (-) ": "Dimension de plongement m de la RQA (AP) : faux plus proches voisins < 1 % (Kennel et al., 1992).",
    "ML embedding delay    (s) ": "Délai de plongement τ de la RQA (ML, s) : premier minimum de l'information mutuelle moyenne.",
    "AP embedding delay    (s) ": "Délai de plongement τ de la RQA (AP, s) : premier minimum de l'information mutuelle moyenne.",
}


# -----------------------------------------------------------------------------
# Textes de l'interface (anglais -> français)
# -----------------------------------------------------------------------------
FR = {
    # Onglets et cadres d'analyse
    "Acquisition":                      "Acquisition",
    "Analysis":                         "Analyse",
    "Positional Parameters":            "Positionnels",
    "Dynamic Parameters":               "Dynamiques",
    "Spectral Analysis":                "Spectraux",
    "Stochastic & Nonlinear":           "Stochastiques & non linéaires",
    "Logs":                             "Journal",
    "Center Position & Dispersion":     "Position & dispersion",
    "Distances & Amplitudes":           "Distances & amplitudes",
    "Geometry & Direction":             "Géométrie & direction",
    "Duration-dep. Metrics":            "Dépendants de la durée",
    "Velocities":                       "Vitesses",
    "Temporal Frequencies":             "Fréquences temporelles",
    "Advanced Dynamics":                "Dynamique avancée",
    "Spectral Parameters":              "Paramètres spectraux",
    "Frequency Metrics":                "Fréquences",
    "Band Energies":                    "Énergies par bande",
    "Stochastic Parameters":            "Paramètres stochastiques",
    "Nonlinear Parameters":             "Paramètres non linéaires",
    "Stabilogram Diffusion analysis":   "Diffusion du stabilogramme",
    "Critical Time & MSD":              "Temps critique & MSD",
    "Sample Entropy":                   "Entropie d'échantillon",
    "Detrended Fluctuation Analysis":   "DFA",
    "Recurrence Quantification":        "Analyse des récurrences",
    "RQA Embedding":                    "Plongement RQA",

    # Panneau de gauche (analyse)
    "Recordings (OpenSway / BrainBloX)": "Enregistrements (OpenSway / BrainBloX)",
    "Add files...":                     "Ajouter fichiers…",
    "Add folder...":                    "Ajouter dossier…",
    "View:":                            "Vue :",
    "Files":                            "Fichiers",
    "Subjects":                         "Sujets",
    "File":                             "Fichier",
    "Subject":                          "Sujet",
    "Cond.":                            "Cond.",
    "Edit selection...":                "Modifier la sélection…",
    "Empty list":                       "Vider la liste",
    "Advanced settings...":             "Réglages avancés…",
    "Process filelist":                 "Analyser la liste",
    "Compare...":                       "Comparer…",
    "Export selected report":           "Rapport PDF de la sélection",
    "Export all results":               "Exporter tous les résultats",
    "Group":                            "Groupe",
    "Time":                             "Temps",
    "Condition":                        "Condition",
    "Set Subject / factors for the selected files (empty field = unchanged),\n"
    "and rename the factors. A single cell can also be edited by double-click.\n"
    "\nSubject and trial n° are read from file names (ID_1 or ID_n°1),\n"
    "factors from the parent folder name (group_time),\n"
    "eyes and surface from an OpenSway condition folder (YO-dur).":
        "Définir le sujet / les facteurs des fichiers sélectionnés (champ vide = inchangé)\n"
        "et renommer les facteurs. Une cellule se modifie aussi par double-clic.\n"
        "\nSujet et n° d'essai sont lus dans le nom de fichier (ID_1 ou ID_n°1),\n"
        "les facteurs dans le nom du dossier parent (groupe_temps),\n"
        "yeux et surface dans un dossier de condition OpenSway (YO-dur).\n"
        "Pour les fichiers OpenSway, l'en-tête du fichier fait foi.",

    # Dialogues
    "Rename factor":                    "Renommer le facteur",
    "New name for '{}':":               "Nouveau nom pour « {} » :",
    "'{}' is already used.":            "« {} » est déjà utilisé.",
    "Edit selection":                   "Modifier la sélection",
    "Switch to the 'Files' view to edit the design.":
        "Passer en vue « Fichiers » pour modifier le plan.",
    "Values for the {} selected file(s)": "Valeurs pour le(s) {} fichier(s) sélectionné(s)",
    "Factor names":                     "Noms des facteurs",
    "(empty field = unchanged)":        "(champ vide = inchangé)",
    "No file selected: only factor names can be changed.":
        "Aucun fichier sélectionné : seuls les noms de facteurs sont modifiables.",
    "Factor 1":                         "Facteur 1",
    "Factor 2":                         "Facteur 2",
    "Factor names must differ from each other\nand from 'File', 'Subject', 'Trial'.":
        "Les noms de facteurs doivent être différents\nentre eux et de « Fichier », « Sujet », « Essai ».",
    "Cancel":                           "Annuler",
    "OK":                               "OK",
    "Advanced settings":                "Réglages avancés",
    "Reset to defaults":                "Valeurs par défaut",
    "Invalid value for '{}'.":          "Valeur invalide pour « {} ».",
    "Interface":                        "Interface",
    "Language":                         "Langue",
    "Settings":                         "Réglages",
    "Apply":                            "Appliquer",
    "Changes are applied with the « Apply » button.":
        "Les modifications s'appliquent avec le bouton « Appliquer ».",
    "Settings applied: results will be recomputed.":
        "Réglages appliqués : les résultats seront recalculés.",
    "No change.":                       "Aucun changement.",
    "Restart OpenSway now to change the language?\n(the board will be disconnected)":
        "Redémarrer OpenSway maintenant pour changer de langue ?\n(la planche sera déconnectée)",
    "The language will change at the next start of OpenSway.":
        "La langue changera au prochain démarrage d'OpenSway.",

    # Groupes et réglages avancés
    "Preprocessing":                    "Pré-traitement",
    "Dynamic":                          "Dynamique",
    "Spectral":                         "Spectral",
    "Stochastic":                       "Stochastique",
    "Essentials":                       "Essentiel",
    "Size & direction":                 "Taille et direction",
    "Velocity":                         "Vitesse",
    "Frequency":                        "Fréquence",
    "Complexity":                       "Complexité",
    "Selection: one or two descriptors per dimension\n(after Rocchi et al., 2004). All the others are\nin the following tabs and in the export.":
        "Sélection : un ou deux descripteurs par dimension\n(d'après Rocchi et al., 2004). Tous les autres\nsont dans les onglets suivants et dans l'export.",
    "DFA":                              "DFA",
    "RQA":                              "RQA",
    "Resampling method":                "Ré-échantillonnage",
    "SWARII window (s)":                "Fenêtre SWARII (s)",
    "Target frequency (Hz)":            "Fréquence cible (Hz)",
    "Lowpass cutoff (Hz)":              "Coupure passe-bas (Hz)",
    "Butterworth order":                "Ordre Butterworth",
    "Savitzky-Golay smoothing":         "Lissage Savitzky-Golay",
    "SG window (s)":                    "Fenêtre SG (s)",
    "SG polynomial order":              "Ordre du polynôme SG",
    "Welch segment (s)":                "Segment de Welch (s)",
    "SDA breakpoint min (s)":           "Rupture SDA min. (s)",
    "SDA breakpoint max (s)":           "Rupture SDA max. (s)",
    "Embedding dimension m":            "Dimension m",
    "Tolerance r (x SD)":               "Tolérance r (× ET)",
    "On COP increments":                "Sur les incréments du CoP",
    "Smallest window (samples)":        "Plus petite fenêtre (éch.)",
    "Short/long crossover (s)":         "Transition court/long (s)",
    "Radius mode":                      "Mode du rayon",
    "Fixed recurrence rate (0-1)":      "Taux de récurrence fixe (0-1)",
    "Fixed radius (x mean dist.)":      "Rayon fixe (× dist. moy.)",
    "Min. diagonal line (pts)":         "Diagonale min. (pts)",
    "FNN threshold (0-1)":              "Seuil FNN (0-1)",
    "Max. embedding dimension":         "Dimension max.",

    # Messages
    "Export Error":                     "Erreur d'export",
    "No file in the list.":             "Aucun fichier dans la liste.",
    "No metrics available to export.":  "Aucun résultat à exporter.",
    "Export report":                    "Rapport PDF",
    "Please select at least one file in the list.":
        "Sélectionne au moins un fichier dans la liste.",
    "Please select at least one subject in the list.":
        "Sélectionne au moins un sujet dans la liste.",
    "Export report as PDF":             "Enregistrer le rapport PDF",
    "Export patient report as PDF":     "Enregistrer le rapport patient PDF",
    "Select OpenSway / BrainBloX recordings": "Choisir des enregistrements OpenSway / BrainBloX",
    "Select a folder (csv files, sub-folders: group_time)":
        "Choisir un dossier (fichiers csv, sous-dossiers : groupe_temps)",

    # Tracés
    "centered stabilogram":             "stabilogramme centré",
    "centered stabilograms":            "stabilogrammes centrés",
    "trials":                           "essais",
    "statokinesigram":                  "statokinésigramme",
    "statokinesigrams":                 "statokinésigrammes",
    "Frequency (Hz)":                   "Fréquence (Hz)",
    "Power density":                    "Densité de puissance",
    "Normalized Band Energy distribution": "Énergie par bande (normalisée)",
    "Stabilogram diffusion plot":       "Diffusion du stabilogramme",
    "DFA fluctuation function":         "Fonction de fluctuation (DFA)",
    "Window size (s)":                  "Taille de fenêtre (s)",
    "recurrence plot":                  "tracé de récurrence",
    "Time (s)":                         "Temps (s)",
    "mean":                             "moyenne",
    "trial":                            "essai",
    "mean of {}":                       "moyenne de {}",
    "mean centre":                      "centre moyen",
    "Reading files...":                 "Lecture des fichiers…",
    "Analysing trials...":              "Analyse des essais…",
    "Analysing files...":               "Analyse des fichiers…",
    "Writing the report...":            "Rédaction du rapport…",
    "Comparing...":                     "Comparaison…",
    "all conditions":                   "toutes conditions",
    "reference":                        "référence",
    "Reference":                        "Référence",
    "unusual values":                   "valeurs inhabituelles",
    "Reference values":                 "Valeurs de référence",
    "No reference file":                "Aucun fichier de référence",
    "Load...":                          "Charger…",
    "Template...":                      "Modèle…",
    "Remove":                           "Retirer",
    "Threshold |z| (orange)":           "Seuil |z| (orange)",
    "Threshold |z| (red)":              "Seuil |z| (rouge)",
    "Reference values: one row per descriptor (metric, mean, sd),\noptionally per condition (eyes YO/YF, surface dur/mousse).\n"
    "Values with |z| above the thresholds are coloured in the Analysis tab.\n"
    "« Template... » creates the file to fill in.":
        "Valeurs de référence : une ligne par descripteur (metric, mean, sd),\néventuellement par condition (eyes YO/YF, surface dur/mousse).\n"
        "Les valeurs dont |z| dépasse les seuils sont colorées dans l'onglet Analyse.\n"
        "« Modèle… » crée le fichier à remplir.",
    "Choose a reference file":          "Choisir un fichier de référence",
    "Save the template":                "Enregistrer le modèle",
    "Template saved: fill in the mean and sd columns, then load it.":
        "Modèle enregistré : remplir les colonnes mean et sd, puis le charger.",
    "Reference file loaded: {} descriptor(s).": "Fichier de référence chargé : {} descripteur(s).",
    "mean statokinesigram":             "statokinésigramme moyen",
    "sway amplitude":                   "amplitude d'oscillation",
    "moving SD":                        "ET glissant",
    "Plots:":                           "Graphes :",
    "Trials":                           "Essais",
    "Mean":                             "Moyenne",
    "Trials: each trial plotted.\nMean: mean 95 % ellipse (mean axes and orientation),\n"
    "mean centre ± 1 SD, and sway amplitude (2 s moving SD) mean ± 1 SD.\n"
    "Raw displacements are not averaged: trials are not synchronised in time.":
        "Essais : chaque essai est tracé.\nMoyenne : ellipse 95 % moyenne (axes et orientation moyens),\n"
        "centre moyen ± 1 ET, et amplitude d'oscillation (ET glissant 2 s) moyenne ± 1 ET.\n"
        "Les déplacements bruts ne sont pas moyennés : les essais ne sont pas synchronisés.",
}


# -----------------------------------------------------------------------------
# Textes rédigés en français (acquisition) : traduction vers l'anglais
# -----------------------------------------------------------------------------
def fr(text: str) -> str:
    if _lang == "fr":
        return text
    return EN.get(text, text)


EN = {
    "Planche":                          "Board",
    "Simulateur":                       "Simulator",
    "Connecter":                        "Connect",
    "Tare":                             "Tare",
    "Déconnecter":                      "Disconnect",
    "Mise à zéro des 4 capteurs, planche VIDE.\nÀ refaire si la planche a été déplacée.":
        "Zeroes the 4 sensors, board EMPTY.\nRedo it if the board has been moved.",
    "Statut":                           "Status",
    "Batterie":                         "Battery",
    "Charge":                           "Load",
    "Non connectée":                    "Not connected",
    "non faite":                        "not done",
    "en cours…":                        "running…",
    "faite":                            "done",
    "échec":                            "failed",
    "Sujet & conditions":               "Subject & conditions",
    "Sujet (code)":                     "Subject (code)",
    "Groupe":                           "Group",
    "Temps":                            "Time",
    "Yeux":                             "Eyes",
    "Surface":                          "Surface",
    "Yeux ouverts":                     "Eyes open",
    "Yeux fermés":                      "Eyes closed",
    "Sol dur":                          "Firm",
    "Mousse":                           "Foam",
    "Note":                             "Note",
    "Code pseudonyme du sujet (ex. S012).\nÉviter nom / prénom : il figure dans le nom du fichier.":
        "Pseudonymous subject code (e.g. S012).\nAvoid names: it appears in the file name.",
    "Facultatif (ex. ttt, sim). Avec le temps, donne le dossier\n« groupe_temps », reconnu à l'analyse comme dans la v2.3.":
        "Optional (e.g. ttt, sim). With the time point, gives the folder\n\"group_time\", recognised by the analysis as in v2.3.",
    "Facultatif (ex. AV, AP, T0, T1).": "Optional (e.g. pre, post, T0, T1).",
    "Protocole":                        "Protocol",
    "Durée (s)":                        "Duration (s)",
    "Nombre d'essais":                  "Number of trials",
    "Pause (s)":                        "Rest (s)",
    "Décompte (s)":                     "Countdown (s)",
    "Attendre ma validation entre essais": "Wait for my click between trials",
    "Si coché, l'essai suivant ne démarre qu'au clic sur « Essai suivant »\n(sinon il démarre automatiquement après la pause).":
        "If checked, the next trial starts only when clicking \"Next trial\"\n(otherwise it starts automatically after the rest).",
    "60 s par défaut : au moins 60 s pour l'entropie d'échantillon\n(Montesinos et al., 2018) ; 90 s pour la fiabilité des\nparamètres classiques (Ruhe et al., 2010).":
        "60 s by default: at least 60 s for sample entropy\n(Montesinos et al., 2018); 90 s for the reliability of\ntraditional parameters (Ruhe et al., 2010).",
    "3 essais par défaut : moyenner 3 à 5 répétitions\n(Ruhe et al., 2010).":
        "3 trials by default: average 3 to 5 repetitions\n(Ruhe et al., 2010).",
    "Dossier d'enregistrement":         "Recording folder",
    "Démarrer":                         "Start",
    "Arrêter":                          "Stop",
    "Essai suivant":                    "Next trial",
    "ML (cm)   gauche ← → droite":      "ML (cm)   left ← → right",
    "AP (cm)   arrière ← → avant":      "AP (cm)   back ← → front",
    "Centre de pression (temps réel)":  "Centre of pressure (live)",
    "10 dernières secondes":            "Last 10 seconds",
    "Temps (s)":                        "Time (s)",
    "Connexion…":                       "Connecting…",
    "Connexion":                        "Connection",
    "Planche non trouvée":              "Board not found",
    "La planche n'est pas connectée.\n\nAppuie sur le bouton rouge SYNC (sous le capot des piles) :\nla LED clignote. Puis clique sur OK.\n\n(Si la planche a déjà été appairée sur ce PC, le bouton POWER\npeut suffire : appuie dessus puis clique sur Annuler et réessaie.)":
        "The board is not connected.\n\nPress the red SYNC button (under the battery cover):\nthe LED blinks. Then click OK.\n\n(If the board was already paired with this PC, the POWER button\nmay be enough: press it, click Cancel and try again.)",
    "Appairage…":                       "Pairing…",
    "[BT] Appairage en cours (jusqu'à 1 min 30)…": "[BT] Pairing (up to 1 min 30)…",
    "[Connexion] Recherche de la planche (jusqu'à 15 s)…": "[Connection] Looking for the board (up to 15 s)…",
    "Réessaie : bouton SYNC puis Connecter.": "Try again: SYNC button, then Connect.",
    "Calibration usine":                "Factory calibration",
    "Faire la tare maintenant ?\n(planche vide)": "Tare now?\n(empty board)",
    "Personne sur la planche ?\nClique sur OK, la tare dure 2 s.":
        "Nobody on the board?\nClick OK, the tare takes 2 s.",
    "mesures":                          "samples",
    "Connecte d'abord la planche (ou le simulateur).": "Connect the board (or the simulator) first.",
    "Renseigne le code du sujet.":      "Enter the subject code.",
    "Paramètres du protocole invalides (durée ≥ 5 s, essais ≥ 1).":
        "Invalid protocol settings (duration ≥ 5 s, trials ≥ 1).",
    "La tare n'a pas été faite. Continuer ?": "The tare has not been done. Continue?",
    "Personne ne semble être sur la planche.\nDémarrer quand même ?":
        "Nobody seems to be on the board.\nStart anyway?",
    "Série":                            "Series",
    "Essai":                            "Trial",
    "essai":                            "trial",
    "interrompu (non enregistré).":     "interrupted (not saved).",
    "Série arrêtée.":                   "Series stopped.",
    "[Série] Essai vide ou trop court : vérifier la connexion.":
        "[Series] Empty or too short trial: check the connection.",
    "Erreur : essai vide.":             "Error: empty trial.",
    "Enregistrement":                   "Recording",
    "Impossible d'écrire le fichier :": "Cannot write the file:",
    "Erreur d'écriture.":               "Write error.",
    "Série terminée":                   "Series completed",
    "Planche perdue":                   "Board lost",
    "Connexion perdue.":                "Connection lost.",
    "La planche s'est déconnectée.\nVérifie les piles puis reconnecte.":
        "The board disconnected.\nCheck the batteries and reconnect.",
    "départ dans":                      "starts in",
    "dans":                             "in",
    "Prêt pour l'essai":                "Ready for trial",
    "clique sur « Essai suivant »":     "click \"Next trial\"",
    "connexion établie.":               "connected.",
    "Module 'hidapi' absent : pip install hidapi (inutile avec le .exe).":
        "Module 'hidapi' missing: pip install hidapi (not needed with the .exe).",
    "Appairage échoué.":                "Pairing failed.",
    "Appairage automatique disponible sous Windows uniquement.":
        "Automatic pairing is only available on Windows.",
    "Wii Balance Board appairée et connectée.": "Wii Balance Board paired and connected.",
    "Appairage fait, mais la planche n'apparaît pas.": "Paired, but the board does not show up.",
    "Un enregistrement est en cours. Quitter ?": "A recording is running. Quit?",
}
