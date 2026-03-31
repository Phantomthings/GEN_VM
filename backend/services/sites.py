PROJECTS = [
    "8822_001", "8822_002", "8822_003",
    "8822_004", "8822_005", "8822_006", "8822_007",
    "8822_008", "8822_009", "8822_011", "8822_012",
]

MAPPING_SITES = {
    "001": "Saint-Jean-de-Maurienne",
    "002": "La Rochelle",
    "003": "Pouilly-en-Auxois",
    "004": "Carvin",
    "005": "Blois",
    "006": "Pau - Novotel",
    "007": "Valserhone",
    "008": "Courtenay",
    "009": "Valframbert",
    "011": "Chaufour les Bonnieres",
    "012": "Roye 2",
}


def label_site(code: str) -> str:
    suffix = code.split("_")[-1]
    return MAPPING_SITES.get(suffix, code)


def get_projects() -> list[dict]:
    return [
        {"code": p, "label": label_site(p)}
        for p in PROJECTS
    ]
