// =============================================================================
// GEOMETRIE 2D COMPLETE - Visualisation du maillage blockMesh
// =============================================================================
// Ce fichier .geo est pour VISUALISATION uniquement dans Gmsh
// Le maillage réel est généré par blockMesh (system/blockMeshDict)
//
// Géométrie: 16 blocs, simulation 2D (empty en z)
// Date: 2025-12-01
// =============================================================================

// Échelle: mm (comme blockMeshDict avec scale 0.001)

// === DIMENSIONS ===
// Domaine X
x_isolant_left = -0.8;
x_puit_left = -0.4;
x_buse_left = -0.15;
x_center = 0;
x_buse_right = 0.15;
x_puit_right = 0.4;
x_isolant_right = 0.8;

// Domaine Y
y_substrate = 0;
y_puit_top = 0.128;      // Hauteur puit
y_gap = 0.158;           // Bas buse / haut gap (30µm gap)
y_air_top = 0.278;       // Haut domaine air
y_buse_top = 0.598;      // Haut buse (inlet) - hauteur buse 0.44mm

// Épaisseur 2D (direction z)
z_front = 0;
z_back = 0.1;

// === MESH SIZE ===
lc = 0.02;  // Taille caractéristique pour visualisation

// =============================================================================
// POINTS - Face avant (z=0)
// =============================================================================

// Niveau y=0 (substrat)
Point(1) = {x_isolant_left, y_substrate, z_front, lc};
Point(2) = {x_puit_left, y_substrate, z_front, lc};
Point(3) = {x_buse_left, y_substrate, z_front, lc};
Point(4) = {x_center, y_substrate, z_front, lc};
Point(5) = {x_buse_right, y_substrate, z_front, lc};
Point(6) = {x_puit_right, y_substrate, z_front, lc};
Point(7) = {x_isolant_right, y_substrate, z_front, lc};

// Niveau y=0.128 (haut puit)
Point(11) = {x_isolant_left, y_puit_top, z_front, lc};
Point(12) = {x_puit_left, y_puit_top, z_front, lc};
Point(13) = {x_buse_left, y_puit_top, z_front, lc};
Point(14) = {x_center, y_puit_top, z_front, lc};
Point(15) = {x_buse_right, y_puit_top, z_front, lc};
Point(16) = {x_puit_right, y_puit_top, z_front, lc};
Point(17) = {x_isolant_right, y_puit_top, z_front, lc};

// Niveau y=0.158 (bas buse)
Point(21) = {x_isolant_left, y_gap, z_front, lc};
Point(22) = {x_puit_left, y_gap, z_front, lc};
Point(23) = {x_buse_left, y_gap, z_front, lc};
Point(24) = {x_center, y_gap, z_front, lc};
Point(25) = {x_buse_right, y_gap, z_front, lc};
Point(26) = {x_puit_right, y_gap, z_front, lc};
Point(27) = {x_isolant_right, y_gap, z_front, lc};

// Niveau y=0.278 (haut air)
Point(31) = {x_isolant_left, y_air_top, z_front, lc};
Point(32) = {x_puit_left, y_air_top, z_front, lc};
Point(33) = {x_buse_left, y_air_top, z_front, lc};
Point(35) = {x_buse_right, y_air_top, z_front, lc};
Point(36) = {x_puit_right, y_air_top, z_front, lc};
Point(37) = {x_isolant_right, y_air_top, z_front, lc};

// Niveau y=0.598 (haut buse / inlet)
Point(43) = {x_buse_left, y_buse_top, z_front, lc};
Point(44) = {x_center, y_buse_top, z_front, lc};
Point(45) = {x_buse_right, y_buse_top, z_front, lc};

// =============================================================================
// LIGNES - Contours des régions
// =============================================================================

// --- SUBSTRAT (y=0) ---
Line(101) = {2, 3};   // Puit gauche
Line(102) = {3, 4};   // Puit centre-gauche
Line(103) = {4, 5};   // Puit centre-droite
Line(104) = {5, 6};   // Puit droite

// --- PAROIS PUIT (verticales) ---
Line(111) = {2, 12};  // Isolant gauche (CA=15°)
Line(112) = {6, 16};  // Isolant droite (CA=160°)

// --- HAUT PUIT (y=0.128) ---
Line(121) = {11, 12}; // Top isolant gauche
Line(122) = {12, 13};
Line(123) = {13, 14};
Line(124) = {14, 15};
Line(125) = {15, 16};
Line(126) = {16, 17}; // Top isolant droite

// --- GAP AIR (y=0.128 -> y=0.158) ---
Line(131) = {12, 22};
Line(132) = {13, 23};
Line(133) = {15, 25};
Line(134) = {16, 26};

// --- BAS BUSE (y=0.158) ---
Line(141) = {21, 22};
Line(142) = {22, 23};
Line(143) = {23, 24};
Line(144) = {24, 25};
Line(145) = {25, 26};
Line(146) = {26, 27};

// --- PAROIS BUSE (verticales) ---
Line(151) = {23, 33}; // Buse ext gauche (CA=180°)
Line(152) = {25, 35}; // Buse ext droite (CA=180°)
Line(153) = {33, 43}; // Buse int gauche (CA=90°)
Line(154) = {35, 45}; // Buse int droite (CA=90°)

// --- HAUT AIR (y=0.278) ---
Line(161) = {31, 32};
Line(162) = {32, 33};
Line(165) = {35, 36};
Line(166) = {36, 37};

// --- INLET BUSE (y=0.598) ---
Line(171) = {43, 44};
Line(172) = {44, 45};

// --- CONNEXIONS VERTICALES RESTANTES ---
Line(181) = {11, 21};
Line(182) = {21, 31};
Line(183) = {17, 27};
Line(184) = {27, 37};

// =============================================================================
// SURFACES (pour visualisation)
// =============================================================================

// PUIT (4 sections)
Curve Loop(201) = {101, -Line{3,13}, -122, -111};
// (Simplification - juste les contours principaux pour visualisation)

// =============================================================================
// PHYSICAL GROUPS - Correspondance avec blockMeshDict patches
// =============================================================================

// Substrat (fond puit) - CA=35°
Physical Curve("substrate") = {101, 102, 103, 104};

// Paroi isolant gauche - CA=15° (hydrophile)
Physical Curve("wall_isolant_left") = {111};

// Paroi isolant droite - CA=160° (hydrophobe)
Physical Curve("wall_isolant_right") = {112};

// Top isolant gauche - CA=15°
Physical Curve("top_isolant_left") = {121};

// Top isolant droite - CA=160°
Physical Curve("top_isolant_right") = {126};

// Buse intérieur gauche - CA=90°
Physical Curve("wall_buse_left_int") = {153};

// Buse extérieur gauche - CA=180°
Physical Curve("wall_buse_left_ext") = {151};

// Buse intérieur droite - CA=90°
Physical Curve("wall_buse_right_int") = {154};

// Buse extérieur droite - CA=180°
Physical Curve("wall_buse_right_ext") = {152};

// Inlet (haut buse)
Physical Curve("inlet") = {171, 172};

// Atmosphere (haut air)
Physical Curve("atmosphere") = {161, 162, 165, 166};

// =============================================================================
// ANNOTATIONS (pour visualisation dans Gmsh)
// =============================================================================
//
// ANGLES DE CONTACT:
// ------------------
// substrate:           35° (or, hydrophile)
// wall_isolant_left:   15° (très hydrophile)
// wall_isolant_right: 160° (hydrophobe)
// top_isolant_left:    15°
// top_isolant_right:  160°
// wall_buse_*_int:     90° (neutre)
// wall_buse_*_ext:    180° (super-hydrophobe)
//
// DIMENSIONS:
// -----------
// Diamètre puit:  800 µm (-0.4 à 0.4 mm)
// Hauteur puit:   128 µm
// Diamètre buse:  300 µm (-0.15 à 0.15 mm)
// Hauteur buse:   440 µm (0.158 à 0.598 mm)
// Gap air:         30 µm (0.128 à 0.158 mm)
//
// =============================================================================
