"""Propiedades de seccion (cm, kg).  Perfiles AISC capturados a mano del manual
(pulgadas -> cm), tablas de usuario del propio archivo STAAD y prismaticos."""
import math
from dataclasses import dataclass

IN = 2.54


@dataclass
class Sec:
    name: str
    shape: str           # 'W', 'HSSR' (rect/cuadrado), 'PIPE', 'ROD', 'GEN', 'TUBEUPT'
    A: float
    Iz: float            # eje fuerte (local z de STAAD)
    Iy: float
    J: float
    Sz: float = 0.0
    Sy: float = 0.0
    Zz: float = 0.0
    Zy: float = 0.0
    Ay: float = 0.0      # area de cortante paralela a y local (alma)
    Az: float = 0.0
    d: float = 0.0
    bf: float = 0.0
    tw: float = 0.0
    tf: float = 0.0
    Cw: float = 0.0
    k: float = 0.0       # k de diseño (W)
    t: float = 0.0       # espesor de pared (HSS / tubo)
    extra: dict = None

    @property
    def rz(self):
        return math.sqrt(self.Iz / self.A)

    @property
    def ry(self):
        return math.sqrt(self.Iy / self.A)


# W: A d tw bf tf Ix Zx Sx Iy Zy Sy J Cw kdes   (pulgadas, AISC 15a ed.)
_W = {
    'W14X22': (6.49, 13.7, 0.230, 5.00, 0.335, 199, 33.2, 29.0, 7.00, 4.39, 2.80, 0.208, 314, 0.735),
    'W14X26': (7.69, 13.9, 0.255, 5.03, 0.420, 245, 40.2, 35.3, 8.91, 5.54, 3.55, 0.358, 405, 0.820),
    'W14X30': (8.85, 13.8, 0.270, 6.73, 0.385, 291, 47.3, 42.0, 19.6, 8.99, 5.82, 0.380, 887, 0.785),
    'W14X34': (10.0, 14.0, 0.285, 6.75, 0.455, 340, 54.6, 48.6, 23.3, 10.6, 6.91, 0.569, 1070, 0.855),
    'W14X38': (11.2, 14.1, 0.310, 6.77, 0.515, 385, 61.5, 54.6, 26.7, 12.1, 7.88, 0.798, 1230, 0.915),
    'W12X22': (6.48, 12.3, 0.260, 4.03, 0.425, 156, 29.3, 25.4, 4.66, 3.66, 2.31, 0.293, 164, 0.725),
    'W12X26': (7.65, 12.2, 0.230, 6.49, 0.380, 204, 37.2, 33.4, 17.3, 8.17, 5.34, 0.300, 607, 0.680),
    'W12X30': (8.79, 12.3, 0.260, 6.52, 0.440, 238, 43.1, 38.6, 20.3, 9.56, 6.24, 0.457, 720, 0.740),
    'W12X35': (10.3, 12.5, 0.300, 6.56, 0.520, 285, 51.2, 45.6, 24.5, 11.5, 7.47, 0.741, 879, 0.820),
    'W12X40': (11.7, 11.9, 0.295, 8.01, 0.515, 307, 57.0, 51.5, 44.1, 16.8, 11.0, 0.906, 1440, 1.02),
    'W10X22': (6.49, 10.2, 0.240, 5.75, 0.360, 118, 26.0, 23.2, 11.4, 6.10, 3.97, 0.239, 275, 0.660),
    'W10X26': (7.61, 10.3, 0.260, 5.77, 0.440, 144, 31.3, 27.9, 14.1, 7.50, 4.89, 0.402, 345, 0.740),
    'W10X30': (8.84, 10.5, 0.300, 5.81, 0.510, 170, 36.6, 32.4, 16.7, 8.84, 5.75, 0.622, 414, 0.810),
    'W10X33': (9.71, 9.73, 0.290, 7.96, 0.435, 171, 38.8, 35.0, 36.6, 14.0, 9.20, 0.583, 791, 0.935),
    'W16X26': (7.68, 15.7, 0.250, 5.50, 0.345, 301, 44.2, 38.4, 9.59, 5.48, 3.49, 0.262, 565, 0.747),
    'W16X31': (9.13, 15.9, 0.275, 5.53, 0.440, 375, 54.0, 47.2, 12.4, 7.03, 4.49, 0.461, 739, 0.842),
    'W16X36': (10.6, 15.9, 0.295, 6.99, 0.430, 448, 64.0, 56.5, 24.5, 10.8, 7.00, 0.545, 1460, 0.832),
    'W16X40': (11.8, 16.0, 0.305, 7.00, 0.505, 518, 73.0, 64.7, 28.9, 12.7, 8.25, 0.794, 1730, 0.907),
    'W18X35': (10.3, 17.7, 0.300, 6.00, 0.425, 510, 66.5, 57.6, 15.3, 8.06, 5.12, 0.506, 1140, 0.827),
    'W18X40': (11.8, 17.9, 0.315, 6.02, 0.525, 612, 78.4, 68.4, 19.1, 10.0, 6.35, 0.810, 1440, 0.927),
    'W8X18': (5.26, 8.14, 0.230, 5.25, 0.330, 61.9, 17.0, 15.2, 7.97, 4.66, 3.04, 0.172, 122, 0.630),
    'W8X21': (6.16, 8.28, 0.250, 5.27, 0.400, 75.3, 20.4, 18.2, 9.77, 5.69, 3.71, 0.282, 152, 0.700),
    'W8X24': (7.08, 7.93, 0.245, 6.50, 0.400, 82.7, 23.1, 20.9, 18.3, 8.57, 5.63, 0.346, 259, 0.794),
    'W8X31': (9.13, 8.00, 0.285, 8.00, 0.435, 110, 30.4, 27.5, 37.1, 14.1, 9.27, 0.536, 530, 0.829),
}

# HSS cuadrado/rect: A, Ht, B, tdes, Ix, Zx, Sx, Iy, Zy, Sy, J  (pulgadas)
_HSS = {
    'HSST6X6X0.5': (9.74, 6, 6, 0.465, 48.3, 19.8, 16.1, 48.3, 19.8, 16.1, 81.1),
    'HSST6X6X0.375': (7.58, 6, 6, 0.349, 39.5, 15.8, 13.2, 39.5, 15.8, 13.2, 64.6),
    'HSST6X6X0.313': (6.43, 6, 6, 0.291, 34.3, 13.6, 11.4, 34.3, 13.6, 11.4, 55.4),
    'HSST6X6X0.25': (5.24, 6, 6, 0.233, 28.6, 11.2, 9.54, 28.6, 11.2, 9.54, 45.6),
    'HSST6X6X0.188': (3.98, 6, 6, 0.174, 22.3, 8.63, 7.42, 22.3, 8.63, 7.42, 35.0),
    'HSST5X5X0.188': (3.28, 5, 5, 0.174, 12.6, 5.89, 5.03, 12.6, 5.89, 5.03, 19.9),
    'HSST5X5X0.25': (4.30, 5, 5, 0.233, 16.0, 7.61, 6.41, 16.0, 7.61, 6.41, 25.8),
    'HSST4X4X0.25': (3.37, 4, 4, 0.233, 7.80, 4.69, 3.90, 7.80, 4.69, 3.90, 12.8),
    'HSST4X4X0.188': (2.58, 4, 4, 0.174, 6.21, 3.67, 3.10, 6.21, 3.67, 3.10, 10.0),
    'HSST4X4X0.125': (1.77, 4, 4, 0.116, 4.40, 2.56, 2.20, 4.40, 2.56, 2.20, 6.91),
    'HSST3X3X0.125': (1.30, 3, 3, 0.116, 1.78, 1.40, 1.19, 1.78, 1.40, 1.19, 2.84),
    'HSST3X3X0.188': (1.89, 3, 3, 0.174, 2.46, 1.97, 1.64, 2.46, 1.97, 1.64, 4.03),
    'HSST8X8X0.188': (5.37, 8, 8, 0.174, 54.4, 15.7, 13.6, 54.4, 15.7, 13.6, 84.5),
    'HSST8X8X0.25': (7.10, 8, 8, 0.233, 70.7, 20.5, 17.7, 70.7, 20.5, 17.7, 111),
}

# Tubos: A, OD, tdes, I, S, Z, J  (pulgadas) PIPS = estandar (ced 40), PIPX = extra fuerte
_PIPE = {
    'PIPS5': (0.234, 0.840, 0.101, 0.0160, 0.0388, 0.0555, 0.0320),
    'PIPS7': (0.31, 1.05, 0.105, 0.0350, 0.0671, 0.0937, 0.0700),      # A = 2.00 cm2, como lo cuantifica STAAD 22.12
    'PIPS10': (0.469, 1.32, 0.124, 0.0830, 0.126, 0.177, 0.166),
    'PIPS12': (0.625, 1.66, 0.130, 0.184, 0.222, 0.305, 0.368),
    'PIPS15': (0.749, 1.90, 0.135, 0.293, 0.309, 0.421, 0.586),
    'PIPS20': (1.02, 2.38, 0.143, 0.627, 0.528, 0.713, 1.25),
    'PIPX7': (0.407, 1.05, 0.143, 0.0430, 0.0810, 0.119, 0.0850),
    'PIPX10': (0.602, 1.32, 0.166, 0.101, 0.154, 0.221, 0.199),
}


def aisc(name):
    n = name.upper()
    if n in _W:
        A, d, tw, bf, tf, Ix, Zx, Sx, Iy, Zy, Sy, J, Cw, k = _W[n]
        return Sec(n, 'W', A * IN**2, Ix * IN**4, Iy * IN**4, J * IN**4, Sx * IN**3, Sy * IN**3, Zx * IN**3, Zy * IN**3,
                   Ay=d * tw * IN**2, Az=(2.0 / 3.0) * 2 * bf * tf * IN**2,
                   d=d * IN, bf=bf * IN, tw=tw * IN, tf=tf * IN, Cw=Cw * IN**6, k=k * IN)
    if n in _HSS:
        A, H, B, t, Ix, Zx, Sx, Iy, Zy, Sy, J = _HSS[n]
        return Sec(n, 'HSSR', A * IN**2, Ix * IN**4, Iy * IN**4, J * IN**4, Sx * IN**3, Sy * IN**3, Zx * IN**3, Zy * IN**3,
                   Ay=2 * H * t * IN**2 * 0.0 + A * IN**2 * H / (H + B), Az=A * IN**2 * B / (H + B),
                   d=H * IN, bf=B * IN, tw=t * IN, tf=t * IN, t=t * IN)
    if n in _PIPE:
        A, OD, t, I, S, Z, J = _PIPE[n]
        return Sec(n, 'PIPE', A * IN**2, I * IN**4, I * IN**4, J * IN**4, S * IN**3, S * IN**3, Z * IN**3, Z * IN**3,
                   Ay=0.5 * A * IN**2, Az=0.5 * A * IN**2, d=OD * IN, bf=OD * IN, tw=t * IN, tf=t * IN, t=t * IN)
    raise KeyError('perfil AISC no capturado: ' + name)


def tube_thwtdt(TH, WT, DT):
    """TABLE ST TUBE TH t WT b DT d : tubo rectangular de esquinas vivas."""
    t, b, d = TH, WT, DT
    A = b * d - (b - 2 * t) * (d - 2 * t)
    Iz = (b * d**3 - (b - 2 * t) * (d - 2 * t)**3) / 12.0
    Iy = (d * b**3 - (d - 2 * t) * (b - 2 * t)**3) / 12.0
    Am = (b - t) * (d - t)
    J = 4 * Am**2 * t / (2 * ((b - t) + (d - t)))
    Zz = b * d**2 / 4 - (b - 2 * t) * (d - 2 * t)**2 / 4
    Zy = d * b**2 / 4 - (d - 2 * t) * (b - 2 * t)**2 / 4
    return Sec('TUBE%gx%gx%g' % (d, b, t), 'HSSR', A, Iz, Iy, J, Iz / (d / 2), Iy / (b / 2), Zz, Zy,
               Ay=2 * d * t, Az=2 * b * t, d=d, bf=b, tw=t, tf=t, t=t)


def prismatic(spec):
    if 'YD' in spec and 'ZD' not in spec:
        D = spec['YD']
        A = math.pi * D**2 / 4
        I = math.pi * D**4 / 64
        return Sec('ROD%g' % D, 'ROD', A, I, I, 2 * I, I / (D / 2), I / (D / 2), D**3 / 6, D**3 / 6,
                   Ay=0.0, Az=0.0, d=D, bf=D)
    if 'YD' in spec and 'ZD' in spec:
        h, b = spec['YD'], spec['ZD']
        A = b * h
        a_, b_ = max(b, h) / 2, min(b, h) / 2
        J = a_ * b_**3 * (16 / 3 - 3.36 * b_ / a_ * (1 - b_**4 / (12 * a_**4)))
        return Sec('RECT', 'RECT', A, b * h**3 / 12, h * b**3 / 12, J, b * h**2 / 6, h * b**2 / 6, b * h**2 / 4, h * b**2 / 4,
                   Ay=A * 5 / 6, Az=A * 5 / 6, d=h, bf=b)
    A = spec.get('AX')
    return Sec('PRIS', 'GEN', A, spec.get('IZ'), spec.get('IY'), spec.get('IX'))


def from_upt(name, typ, v):
    if typ == 'GENERAL':
        AX, D, TD, B, TB, IZ, IY, IX, SZ, SY, AY, AZ, PZ, PY, HSS, DEE = v[:16]
        return Sec(name, 'GEN', AX, IZ, IY, IX, SZ, SY, PZ, PY, Ay=AY, Az=AZ, d=D, bf=B, tw=TD, tf=TB, Cw=HSS,
                   extra={'DEE': DEE})
    if typ == 'TUBE':
        AX, D, WD, TB, IZ, IY, IX, AY, AZ = v[:9]
        t = TB
        Zz = WD * D**2 / 4 - (WD - 2 * t) * (D - 2 * t)**2 / 4
        Zy = D * WD**2 / 4 - (D - 2 * t) * (WD - 2 * t)**2 / 4
        return Sec(name, 'HSSR', AX, IZ, IY, IX, IZ / (D / 2), IY / (WD / 2), Zz, Zy, Ay=AY, Az=AZ,
                   d=D, bf=WD, tw=t, tf=t, t=t, extra={'upt': True})
    raise KeyError('tipo de tabla no soportado: ' + typ)


def section_for(model, e):
    spec = model.prop[e]
    k = spec['kind']
    if k == 'UPT':
        typ, vals = model.tables[spec['table']][spec['name']]
        return from_upt(spec['name'], typ, vals)
    if k == 'AISC':
        return aisc(spec['name'])
    if k == 'TUBE':
        return tube_thwtdt(spec['TH'], spec['WT'], spec['DT'])
    if k == 'PRIS':
        return prismatic(spec)
    raise KeyError(k)
