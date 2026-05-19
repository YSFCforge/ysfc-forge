"""
YSFC Forge — FM-X Specific Enums

FM-X har 88 algoritmer (1-88).

Källa: Härlett ur Yamahas publicerade MODX M Data List
(© Yamaha Corporation). Endast funktionella fakta 
extraheras, för interoperabilitet med det odokumenterade
Y2L/Y2U-filformatet. Yamahas dokument återdistribueras inte här —
originalet finns hos Yamaha: https://download.yamaha.com
(sök "MODX M Data List").
"""

# Antal FM-X algoritmer
FMX_ALGORITHM_COUNT = 88

# Lista 1-88 (algoritmer har bara nummer, inga namn)
FMX_ALGORITHMS = list(range(1, 89))


def get_algorithm_label(algo_no):
    """Returns display label for algorithm (1-88)."""
    if 1 <= algo_no <= 88:
        return f'Algorithm {algo_no}'
    return f'Invalid({algo_no})'


# OP Spectral Forms (verifierat strukturellt — namn från MODX-manualer)
SPECTRAL_FORMS = {
    0: 'Sin',
    1: 'AC1',
    2: 'AC2',
    3: 'AC3',
    4: 'AC4',
    5: 'AC5',
    6: 'AC6',
    7: 'AC7',
    8: 'AC8',
    # Möjligen fler (kräver verifiering med skärmdumpar)
}


if __name__ == '__main__':
    print(f"FM-X Algorithms: 1-{FMX_ALGORITHM_COUNT}")
    print(f"Spectral Forms: {len(SPECTRAL_FORMS)}")
