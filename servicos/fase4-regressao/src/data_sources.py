"""Importação e validação local de observações oficiais externas."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tempfile
import unicodedata
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.atomic_files import data_directory, publish_files

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_DATA_DIR = ROOT / "src" / "dados" / "official"
NOAA_STATION = "GA_Newton_11_SW"
NOAA_YEAR = 2025
NOAA_URL = (
    "https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/"
    f"{NOAA_YEAR}/CRNH0203-{NOAA_YEAR}-{NOAA_STATION}.txt"
)
NOAA_CSV = OFFICIAL_DATA_DIR / "noaa_uscrn_ga_newton_2025.csv"
NOAA_METADATA = OFFICIAL_DATA_DIR / "noaa_uscrn_ga_newton_2025_metadata.json"
INMET_YEAR = 2025
INMET_STATION_CODE = "A701"
INMET_URL = f"https://portal.inmet.gov.br/uploads/dadoshistoricos/{INMET_YEAR}.zip"
INMET_CSV = OFFICIAL_DATA_DIR / "inmet_sp_a701_2025.csv"
INMET_METADATA = OFFICIAL_DATA_DIR / "inmet_sp_a701_2025_metadata.json"
SIDRA_API = "https://apisidra.ibge.gov.br/values"
SIDRA_CROPS = {
    "2692": "Arroz (em casca)",
    "2702": "Feijão (em grão)",
    "2711": "Milho (em grão)",
    "2713": "Soja (em grão)",
    "2696": "Cana-de-açúcar",
}
SIDRA_START_YEAR = 1990
SIDRA_END_YEAR = 2025
SIDRA_NATIONAL_CSV = OFFICIAL_DATA_DIR / "sidra1612_rendimento_brasil.csv"
SIDRA_MUNICIPAL_CSV = OFFICIAL_DATA_DIR / "sidra1612_rendimento_municipios_2025.csv"
SIDRA_METADATA = OFFICIAL_DATA_DIR / "sidra1612_metadata.json"

NOAA_COLUMNS = [
    "WBANNO", "UTC_DATE", "UTC_TIME", "LST_DATE", "LST_TIME", "CRX_VN",
    "LONGITUDE", "LATITUDE", "T_CALC", "T_HR_AVG", "T_MAX", "T_MIN",
    "P_CALC", "SOLARAD", "SOLARAD_FLAG", "SOLARAD_MAX", "SOLARAD_MAX_FLAG",
    "SOLARAD_MIN", "SOLARAD_MIN_FLAG", "SUR_TEMP_TYPE", "SUR_TEMP",
    "SUR_TEMP_FLAG", "SUR_TEMP_MAX", "SUR_TEMP_MAX_FLAG", "SUR_TEMP_MIN",
    "SUR_TEMP_MIN_FLAG", "RH_HR_AVG", "RH_HR_AVG_FLAG", "SOIL_MOISTURE_5",
    "SOIL_MOISTURE_10", "SOIL_MOISTURE_20", "SOIL_MOISTURE_50",
    "SOIL_MOISTURE_100", "SOIL_TEMP_5", "SOIL_TEMP_10", "SOIL_TEMP_20",
    "SOIL_TEMP_50", "SOIL_TEMP_100",
]
NOAA_OUTPUT_COLUMNS = [
    "timestamp_utc",
    "station",
    "wban",
    "latitude",
    "longitude",
    "air_temperature_c",
    "precipitation_mm",
    "relative_humidity_pct",
    "soil_moisture_5cm_m3_m3",
    "soil_moisture_10cm_m3_m3",
    "soil_moisture_20cm_m3_m3",
    "soil_moisture_50cm_m3_m3",
    "soil_moisture_100cm_m3_m3",
    "soil_temperature_5cm_c",
    "soil_temperature_10cm_c",
    "soil_temperature_20cm_c",
    "soil_temperature_50cm_c",
    "soil_temperature_100cm_c",
]
INMET_OUTPUT_COLUMNS = [
    "timestamp_utc",
    "station",
    "station_code",
    "uf",
    "latitude",
    "longitude",
    "air_temperature_c",
    "precipitation_mm",
    "relative_humidity_pct",
]
SIDRA_OUTPUT_COLUMNS = [
    "codigo_geografico",
    "geografia",
    "municipio",
    "uf",
    "nivel_geografico",
    "codigo_cultura",
    "cultura",
    "ano",
    "rendimento_kg_ha",
    "unidade",
]

# Sentinelas por campo da especificação USCRN hourly02, nota C.
NOAA_SENTINELS = {
    **{column: -9999.0 for column in ["T_CALC", "T_HR_AVG", "T_MAX", "T_MIN", "P_CALC",
        "SUR_TEMP", "SUR_TEMP_MAX", "SUR_TEMP_MIN", "RH_HR_AVG",
        "SOIL_TEMP_5", "SOIL_TEMP_10", "SOIL_TEMP_20", "SOIL_TEMP_50", "SOIL_TEMP_100"]},
    **{column: -99.000 for column in NOAA_COLUMNS if column.startswith("SOIL_MOISTURE_")},
    **{column: -99999 for column in ["SOLARAD", "SOLARAD_MAX", "SOLARAD_MIN"]},
}
_UF_CODES = set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())
_UF_BY_IBGE = dict(zip(
    "11 12 13 14 15 16 17 21 22 23 24 25 26 27 28 29 31 32 33 35 41 42 43 50 51 52 53".split(),
    "RO AC AM RR PA AP TO MA PI CE RN PB PE AL SE BA MG ES RJ SP PR SC RS MS MT GO DF".split(),
))


def _numeric(values: pd.Series, name: str, *, allow_missing: bool = True) -> pd.Series:
    try:
        result = pd.to_numeric(values, errors="raise")
    except (ValueError, TypeError) as error:
        raise ValueError(f"Campo {name} contém valor não numérico.") from error
    if np.isinf(result.to_numpy(dtype=float)).any() or (not allow_missing and result.isna().any()):
        raise ValueError(f"Campo {name} contém valor ausente ou não finito.")
    return result


def _between(values: pd.Series, low: float, high: float, name: str) -> None:
    if not values.dropna().between(low, high).all():
        raise ValueError(f"Campo {name} fora do intervalo [{low}, {high}].")


def _weather_frame(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    columns = NOAA_OUTPUT_COLUMNS if source == "NOAA" else INMET_OUTPUT_COLUMNS
    if frame.columns.duplicated().any() or set(frame.columns) != set(columns):
        raise ValueError(f"Schema {source} local incompatível.")
    frame = frame[columns].copy()
    if frame.empty:
        raise ValueError(f"Arquivo {source} sem observações.")
    times = pd.to_datetime(frame["timestamp_utc"], format="mixed", utc=True, errors="coerce")
    if times.isna().any() or times.duplicated().any() or (times != times.dt.floor("h")).any():
        raise ValueError(f"Arquivo {source} contém timestamp inválido ou duplicado.")
    end = "2026-01-01T00:00:00Z"
    if (times < pd.Timestamp("2025-01-01T00:00:00Z")).any() or (times > pd.Timestamp(end)).any():
        raise ValueError(f"Arquivo {source} contém datas fora de 2025.")
    if source == "INMET" and (times >= pd.Timestamp(end)).any():
        raise ValueError("Arquivo INMET contém datas fora de 2025.")
    if source == "NOAA" and (times <= pd.Timestamp("2025-01-01T00:00:00Z")).any():
        raise ValueError("Período horário NOAA não corresponde a 2025.")
    frame["timestamp_utc"] = times
    text_columns = {"timestamp_utc", "station", "station_code", "uf"}
    for column in set(columns) - text_columns:
        frame[column] = _numeric(frame[column], column, allow_missing=column not in {"latitude", "longitude", "wban"})
    expected_name = "GA Newton 11 SW" if source == "NOAA" else "SAO PAULO - MIRANTE"
    if frame["station"].ne(expected_name).any():
        raise ValueError(f"Identidade da estação {source} incompatível.")
    latitude, longitude = (31.19, -84.45) if source == "NOAA" else (-23.4962888, -46.6200666)
    if not np.isclose(frame["latitude"], latitude, atol=0.01, rtol=0).all() or not np.isclose(frame["longitude"], longitude, atol=0.01, rtol=0).all():
        raise ValueError(f"Coordenadas da estação {source} incompatíveis.")
    if source == "NOAA":
        if frame["wban"].ne(63829).any():
            raise ValueError("Estação NOAA WBAN incompatível com GA Newton 11 SW.")
        frame["wban"] = frame["wban"].astype(int)
        moisture = [column for column in columns if column.startswith("soil_moisture_")]
        for column in moisture:
            _between(frame[column], 0, 1, column)
        if not frame[moisture].notna().any(axis=1).all():
            raise ValueError("Arquivo NOAA contém linha sem umidade do solo observada.")
        for column in columns:
            if column.startswith("soil_temperature_"):
                _between(frame[column], -90, 70, column)
    elif frame["station_code"].ne(INMET_STATION_CODE).any() or frame["uf"].ne("SP").any():
        raise ValueError("Identidade da estação INMET A701/SP incompatível.")
    _between(frame["air_temperature_c"], -90, 70, "air_temperature_c")
    # Limite de plausibilidade por hora, não limiar agronômico ou de alerta.
    _between(frame["precipitation_mm"], 0, 2000, "precipitation_mm")
    _between(frame["relative_humidity_pct"], 0, 100, "relative_humidity_pct")
    if source == "INMET" and not frame[["air_temperature_c", "precipitation_mm", "relative_humidity_pct"]].notna().any(axis=1).all():
        raise ValueError("Arquivo INMET contém linha sem observações meteorológicas.")
    return frame.sort_values("timestamp_utc").reset_index(drop=True)


def _sidra_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.columns.duplicated().any() or set(frame.columns) != set(SIDRA_OUTPUT_COLUMNS) or frame.empty:
        raise ValueError("Schema SIDRA local incompatível ou sem observações.")
    frame = frame[SIDRA_OUTPUT_COLUMNS].copy()
    for column in ["ano", "codigo_cultura", "codigo_geografico"]:
        values = _numeric(frame[column], column, allow_missing=False)
        if (values % 1).ne(0).any():
            raise ValueError(f"Identificador SIDRA {column} inválido.")
        frame[column] = values.astype(int) if column == "ano" else values.astype(int).astype(str)
    _between(frame["ano"], SIDRA_START_YEAR, SIDRA_END_YEAR, "ano")
    if not frame["codigo_cultura"].isin(SIDRA_CROPS).all() or frame["cultura"].ne(frame["codigo_cultura"].map(SIDRA_CROPS)).any():
        raise ValueError("Cultura SIDRA incompatível com a consulta.")
    if frame["unidade"].ne("kg/ha").any() or not frame["nivel_geografico"].isin(["brasil", "municipio"]).all():
        raise ValueError("Unidade ou nível geográfico SIDRA incompatível.")
    for row in frame.itertuples(index=False):
        if row.nivel_geografico == "brasil":
            if row.codigo_geografico != "1" or row.geografia != "Brasil" or pd.notna(row.municipio) or pd.notna(row.uf):
                raise ValueError("Identificação nacional SIDRA incompatível.")
        elif (not re.fullmatch(r"[1-5]\d{6}", row.codigo_geografico) or row.uf not in _UF_CODES
              or _UF_BY_IBGE.get(row.codigo_geografico[:2]) != row.uf
              or not isinstance(row.municipio, str) or not row.municipio.strip()
              or row.geografia != f"{row.municipio} - {row.uf}"):
            raise ValueError("Identificação municipal SIDRA inválida.")
    frame["rendimento_kg_ha"] = _numeric(frame["rendimento_kg_ha"], "rendimento_kg_ha")
    _between(frame["rendimento_kg_ha"], 0, 1_000_000, "rendimento_kg_ha")
    if frame.duplicated(["codigo_geografico", "codigo_cultura", "ano"]).any():
        raise ValueError("Série SIDRA contém chaves duplicadas.")
    return frame


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(text, encoding="utf-8", newline="")
    temporary_path.replace(path)


def _download(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "FarmTech-Solutions-Fase4/1.0 data-ingestion"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"Fonte retornou HTTP {response.status}: {url}")
            content = response.read(50_000_001)
            if len(content) > 50_000_000:
                raise ValueError("Resposta da fonte oficial excede o limite de 50 MB.")
            return content
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"Falha ao adquirir dados de {url}: {error}") from error


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character)).upper().strip()


def parse_noaa_text(content: str, min_valid_observations: int = 1) -> pd.DataFrame:
    """Valida e normaliza um arquivo anual USCRN hourly02 sem inventar medidas."""
    records: list[list[str]] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != len(NOAA_COLUMNS):
            raise ValueError(
                f"Arquivo NOAA inválido na linha {line_number}: "
                f"esperadas {len(NOAA_COLUMNS)} colunas, recebidas {len(fields)}."
            )
        records.append(fields)
    if not records:
        raise ValueError("Arquivo NOAA não contém observações.")

    raw = pd.DataFrame(records, columns=NOAA_COLUMNS)
    numeric_columns = [
        column for column in NOAA_COLUMNS
        if column not in {"UTC_DATE", "UTC_TIME", "LST_DATE", "LST_TIME", "CRX_VN", "SUR_TEMP_TYPE"}
        and not column.endswith("_FLAG")
    ]
    for column in numeric_columns:
        raw[column] = _numeric(raw[column], column, allow_missing=False)
        if column in NOAA_SENTINELS:
            raw[column] = raw[column].replace(NOAA_SENTINELS[column], np.nan)

    timestamps = pd.to_datetime(
        raw["UTC_DATE"] + " " + raw["UTC_TIME"],
        format="%Y%m%d %H%M",
        utc=True,
        errors="coerce",
    )
    if timestamps.isna().any() or timestamps.duplicated().any():
        raise ValueError("Arquivo NOAA contém timestamp inválido.")
    if ((timestamps != timestamps.dt.floor("h")).any()
            or not timestamps.between(pd.Timestamp("2025-01-01T00:00:00Z"), pd.Timestamp("2026-01-01T00:00:00Z"), inclusive="right").all()):
        raise ValueError("Arquivo NOAA contém datas fora de 2025 ou frequência não horária.")
    if raw["WBANNO"].ne(63829).any():
        raise ValueError("Estação NOAA WBAN incompatível com GA Newton 11 SW.")
    if not np.isclose(raw["LATITUDE"], 31.19, atol=0.01, rtol=0).all() or not np.isclose(raw["LONGITUDE"], -84.45, atol=0.01, rtol=0).all():
        raise ValueError("Coordenadas da estação NOAA incompatíveis.")

    frame = pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "station": NOAA_STATION.replace("_", " "),
            "wban": raw["WBANNO"],
            "latitude": raw["LATITUDE"],
            "longitude": raw["LONGITUDE"],
            "air_temperature_c": raw["T_HR_AVG"],
            "precipitation_mm": raw["P_CALC"],
            "relative_humidity_pct": raw["RH_HR_AVG"],
            "soil_moisture_5cm_m3_m3": raw["SOIL_MOISTURE_5"],
            "soil_moisture_10cm_m3_m3": raw["SOIL_MOISTURE_10"],
            "soil_moisture_20cm_m3_m3": raw["SOIL_MOISTURE_20"],
            "soil_moisture_50cm_m3_m3": raw["SOIL_MOISTURE_50"],
            "soil_moisture_100cm_m3_m3": raw["SOIL_MOISTURE_100"],
            "soil_temperature_5cm_c": raw["SOIL_TEMP_5"],
            "soil_temperature_10cm_c": raw["SOIL_TEMP_10"],
            "soil_temperature_20cm_c": raw["SOIL_TEMP_20"],
            "soil_temperature_50cm_c": raw["SOIL_TEMP_50"],
            "soil_temperature_100cm_c": raw["SOIL_TEMP_100"],
        }
    )
    frame = frame[NOAA_OUTPUT_COLUMNS]
    moisture_columns = [column for column in NOAA_OUTPUT_COLUMNS if "soil_moisture_" in column]
    for column in moisture_columns:
        _between(frame[column], 0, 1, column)
    frame.loc[raw["RH_HR_AVG_FLAG"].ne("0"), "relative_humidity_pct"] = np.nan
    valid_moisture = frame[moisture_columns].apply(
        lambda values: values.between(0, 1, inclusive="both")
    ).any(axis=1)
    frame = frame.loc[valid_moisture].copy()
    if len(frame) < min_valid_observations:
        raise ValueError(
            f"Menos de {min_valid_observations} observações válidas de umidade do solo."
        )
    return _weather_frame(frame, "NOAA")


def importar_noaa(
    content: bytes | None = None,
    output_path: Path = NOAA_CSV,
    metadata_path: Path = NOAA_METADATA,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Importa dados locais se informados; sem conteúdo, consulta a fonte pública."""
    source_bytes = content if content is not None else _download(NOAA_URL)
    source_text = source_bytes.decode("ascii")
    frame = parse_noaa_text(source_text, min_valid_observations=24)
    output_path = Path(output_path)
    metadata_path = Path(metadata_path)
    if output_path.resolve() == metadata_path.resolve():
        raise ValueError("CSV e metadados precisam de arquivos distintos.")
    csv_bytes = frame.to_csv(index=False, date_format="%Y-%m-%dT%H:%M:%SZ").encode("utf-8")
    metadata = {
        "fonte": "NOAA National Centers for Environmental Information (NCEI), USCRN",
        "url": NOAA_URL,
        "arquivo_fonte_sha256": _sha256_bytes(source_bytes),
        "arquivo_normalizado": output_path.name,
        "arquivo_normalizado_sha256": _sha256_bytes(csv_bytes),
        "estacao": NOAA_STATION.replace("_", " "),
        "wban": str(frame["wban"].iloc[0]),
        "latitude": float(frame["latitude"].median()),
        "longitude": float(frame["longitude"].median()),
        "inicio_utc": frame["timestamp_utc"].min().isoformat(),
        "fim_utc": frame["timestamp_utc"].max().isoformat(),
        "frequencia": "horária; período de 60 minutos encerrado no timestamp UTC",
        "unidades": {
            "umidade_volumetrica_solo": "m³/m³",
            "temperatura_solo": "°C",
            "temperatura_ar": "°C",
            "precipitacao": "mm por hora",
            "umidade_relativa_ar": "%",
        },
        "tratamento": [
            "Leitura whitespace-delimited de 38 campos conforme HEADERS.txt da USCRN.",
            "Sentinelas por campo conforme hourly02/README.txt: -9999.0 em temperaturas/chuva/UR; -99.000 em umidade do solo; -99999 em radiação.",
            "Mantidas apenas linhas com pelo menos uma umidade do solo finita em [0, 1] m³/m³.",
            "Timestamp mantido em UTC; sem agregação ou imputação.",
        ],
        "observacoes": int(len(frame)),
        "limitacoes": [
            "Estação USCRN nos Estados Unidos; não representa a propriedade do projeto.",
            "Dados de estação meteorológica de referência, não medição do protótipo FarmTech.",
            "Sem equivalência direta com umidade percentual do protótipo; não comparar escalas.",
        ],
        "atualizado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    publish_files({output_path: csv_bytes, metadata_path: json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")})
    return frame, metadata


def parse_inmet_csv(content: bytes, station_code: str = INMET_STATION_CODE) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Interpreta o CSV histórico público do INMET sem preencher lacunas."""
    text = content.decode("latin-1")
    lines = text.splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if _normalize_header(line.split(";")[0].strip()) == "DATA"
            and len(line.split(";")) > 2
        ),
        None,
    )
    if header_index is None:
        raise ValueError("CSV INMET sem linha de cabeçalho de observações.")

    metadata: dict[str, str] = {}
    for line in lines[:header_index]:
        fields = next(csv.reader([line], delimiter=";"))
        if len(fields) >= 2:
            metadata[_normalize_header(fields[0].rstrip(":"))] = fields[1].strip()

    normalized_metadata = {
        _normalize_header(key): value for key, value in metadata.items()
    }
    found_code = normalized_metadata.get("CODIGO (WMO)", "")
    if found_code != station_code:
        raise ValueError(
            f"CSV INMET é da estação {found_code!r}, não da estação {station_code!r}."
        )
    if station_code != INMET_STATION_CODE:
        raise ValueError("Importador configurado exclusivamente para INMET A701.")
    if normalized_metadata.get("ESTACAO") != "SAO PAULO - MIRANTE" or normalized_metadata.get("UF") != "SP":
        raise ValueError("Identidade INMET A701/SP incompatível.")
    try:
        latitude = float(normalized_metadata["LATITUDE"].replace(",", "."))
        longitude = float(normalized_metadata["LONGITUDE"].replace(",", "."))
        altitude = float(normalized_metadata["ALTITUDE"].replace(",", "."))
    except (KeyError, ValueError) as error:
        raise ValueError("Metadados geográficos INMET incompletos ou inválidos.") from error
    if (not np.isfinite([latitude, longitude, altitude]).all()
            or abs(latitude + 23.4962888) > 0.01 or abs(longitude + 46.6200666) > 0.01
            or not -500 <= altitude <= 9000):
        raise ValueError("Coordenadas ou altitude da estação INMET incompatíveis.")

    table = pd.read_csv(
        io.StringIO("\n".join(lines[header_index:])),
        sep=";",
        decimal=",",
        dtype=str,
        keep_default_na=False,
    )
    column_lookup = {_normalize_header(column): column for column in table.columns}
    date_column = column_lookup.get("DATA")
    time_column = column_lookup.get("HORA UTC")
    precip_column = next(
        (
            column
            for normalized, column in column_lookup.items()
            if normalized.startswith("PRECIPITACAO TOTAL, HORARIO")
        ),
        None,
    )
    temperature_column = next(
        (
            column
            for normalized, column in column_lookup.items()
            if normalized.startswith("TEMPERATURA DO AR - BULBO SECO, HORARIA")
        ),
        None,
    )
    humidity_column = next(
        (
            column
            for normalized, column in column_lookup.items()
            if normalized.startswith("UMIDADE RELATIVA DO AR, HORARIA")
        ),
        None,
    )
    if not all([date_column, time_column, precip_column, temperature_column, humidity_column]):
        raise ValueError("CSV INMET não contém as colunas meteorológicas esperadas.")
    if ("(MM)" not in _normalize_header(precip_column)
            or "(°C)" not in _normalize_header(temperature_column)
            or "(%)" not in _normalize_header(humidity_column)):
        raise ValueError("Unidades meteorológicas INMET incompatíveis.")

    timestamps = pd.to_datetime(
        table[date_column].str.strip()
        + " "
        + table[time_column].str.replace(" UTC", "", regex=False).str.strip(),
        format="%Y/%m/%d %H%M",
        utc=True,
        errors="coerce",
    )
    if (timestamps.isna().any() or timestamps.duplicated().any()
            or (timestamps != timestamps.dt.floor("h")).any()
            or not timestamps.between(pd.Timestamp("2025-01-01T00:00:00Z"), pd.Timestamp("2025-12-31T23:00:00Z")).all()):
        raise ValueError("CSV INMET contém timestamp ausente ou inválido.")

    def numeric(column: str) -> pd.Series:
        values = table[column].str.strip().str.replace(",", ".", regex=False)
        return _numeric(values.replace("", np.nan), column).replace(
            {-9999.0: np.nan, -9999: np.nan}
        )

    temperature = numeric(temperature_column)
    precipitation = numeric(precip_column)
    humidity = numeric(humidity_column)
    _between(temperature, -90, 70, "temperatura INMET")
    _between(humidity, 0, 100, "umidade INMET")
    _between(precipitation, 0, 2000, "precipitação INMET")

    frame = pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "station": normalized_metadata.get("ESTACAO", ""),
            "station_code": found_code,
            "uf": normalized_metadata.get("UF", ""),
            "latitude": latitude,
            "longitude": longitude,
            "air_temperature_c": temperature,
            "precipitation_mm": precipitation,
            "relative_humidity_pct": humidity,
        },
        columns=INMET_OUTPUT_COLUMNS,
    )
    observed_columns = [
        "air_temperature_c",
        "precipitation_mm",
        "relative_humidity_pct",
    ]
    frame = frame.loc[frame[observed_columns].notna().any(axis=1)].copy()
    if len(frame) < 100:
        raise ValueError("Menos de 100 observações meteorológicas válidas no CSV INMET.")
    if frame["timestamp_utc"].duplicated().any():
        raise ValueError("CSV INMET contém timestamps duplicados.")
    return _weather_frame(frame, "INMET"), {
        "station": normalized_metadata.get("ESTACAO", ""),
        "station_code": found_code,
        "uf": normalized_metadata.get("UF", ""),
        "latitude": latitude,
        "longitude": longitude,
        "altitude_m": altitude,
    }


def importar_inmet(
    archive_path: Path | None = None,
    output_path: Path = INMET_CSV,
    metadata_path: Path = INMET_METADATA,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Importa CSV de estação INMET de ZIP local ou arquivo anual público."""
    station_code = INMET_STATION_CODE
    with tempfile.TemporaryFile() as archive_file:
        archive_digest = hashlib.sha256()
        if archive_path is None:
            request = urllib.request.Request(
                INMET_URL,
                headers={"User-Agent": "FarmTech-Solutions-Fase4/1.0 data-ingestion"},
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > 200_000_000:
                            raise ValueError("ZIP INMET excede o limite de 200 MB.")
                        archive_file.write(chunk)
                        archive_digest.update(chunk)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
                raise RuntimeError(
                    f"Falha ao adquirir dados INMET de {INMET_URL}: {error}"
                ) from error
            source_url = INMET_URL
        else:
            archive_path = Path(archive_path)
            if not archive_path.is_file():
                raise FileNotFoundError("ZIP INMET local não encontrado.")
            total = archive_path.stat().st_size
            if total > 200_000_000:
                raise ValueError("ZIP INMET local excede o limite de 200 MB.")
            with archive_path.open("rb") as source_file:
                while chunk := source_file.read(1024 * 1024):
                    archive_file.write(chunk)
                    archive_digest.update(chunk)
            source_url = f"arquivo local: {archive_path.name}"

        archive_file.seek(0)
        archive_sha256 = archive_digest.hexdigest()
        try:
            with zipfile.ZipFile(archive_file) as archive:
                candidates = [
                    item
                    for item in archive.infolist()
                    if f"_{station_code}_" in item.filename.upper()
                    and item.filename.upper().endswith(".CSV")
                ]
                if len(candidates) != 1:
                    raise ValueError(
                        f"Esperado um CSV da estação {station_code}, "
                        f"encontrados {len(candidates)}."
                    )
                candidate = candidates[0]
                if candidate.file_size > 25_000_000:
                    raise ValueError("CSV INMET selecionado excede o limite de 25 MB.")
                source_bytes = archive.read(candidate)
        except zipfile.BadZipFile as error:
            raise ValueError("Arquivo de dados INMET não é um ZIP válido.") from error

    frame, station = parse_inmet_csv(source_bytes, station_code=station_code)
    output_path = Path(output_path)
    metadata_path = Path(metadata_path)
    if output_path.resolve() == metadata_path.resolve():
        raise ValueError("CSV e metadados precisam de arquivos distintos.")
    csv_bytes = frame.to_csv(index=False, date_format="%Y-%m-%dT%H:%M:%SZ").encode("utf-8")
    metadata = {
        "fonte": "Instituto Nacional de Meteorologia (INMET), dados históricos observados",
        "url": source_url,
        "arquivo_estacao": candidate.filename,
        "arquivo_zip_sha256": archive_sha256,
        "arquivo_estacao_sha256": _sha256_bytes(source_bytes),
        "arquivo_normalizado": output_path.name,
        "arquivo_normalizado_sha256": _sha256_bytes(csv_bytes),
        **station,
        "inicio_utc": frame["timestamp_utc"].min().isoformat(),
        "fim_utc": frame["timestamp_utc"].max().isoformat(),
        "frequencia": "horária, conforme Hora UTC do arquivo",
        "unidades": {
            "temperatura_ar": "°C",
            "precipitacao": "mm por hora",
            "umidade_relativa_ar": "%",
        },
        "tratamento": [
            "Selecionado somente o CSV oficial da estação A701 dentro do ZIP.",
            "Campos decimais com vírgula convertidos para ponto.",
            "Sentinela -9999 e campos vazios mantidos como ausentes.",
            "Sem imputação; timestamps normalizados para UTC.",
        ],
        "observacoes": int(len(frame)),
        "limitacoes": [
            "Observação meteorológica de estação; não é medição de umidade do solo.",
            "Estação São Paulo - Mirante; não representa necessariamente a propriedade FarmTech.",
            "Dados meteorológicos não foram combinados aos sensores IoT simulados.",
        ],
        "atualizado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    publish_files({output_path: csv_bytes, metadata_path: json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")})
    return frame, metadata


def _sidra_query(geography: str, period: str, crop_codes: str) -> tuple[str, bytes]:
    url = (
        f"{SIDRA_API}/t/1612/{geography}/v/112/p/{period}/c81/{crop_codes}"
    )
    return url, _download(url)


def parse_sidra_json(content: bytes, level: str) -> pd.DataFrame:
    """Valida resposta JSON da tabela SIDRA 1612 e converte rendimento em kg/ha."""
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("Resposta SIDRA não é JSON válido.") from error
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("Resposta SIDRA sem cabeçalho ou registros.")
    required = {
        "D1C", "D1N", "D2C", "D2N", "D3C", "D3N", "D4C", "D4N", "V", "MN"
    }
    if not isinstance(payload[0], dict) or not required.issubset(payload[0]):
        raise ValueError("Schema da API SIDRA 1612 incompatível.")
    if level not in {"brasil", "municipio"}:
        raise ValueError("Nível geográfico SIDRA não suportado.")

    rows = []
    for record in payload[1:]:
        if not isinstance(record, dict) or not required.issubset(record):
            raise ValueError("Schema de registro SIDRA incompatível.")
        if record["D2C"] != "112" or record["D2N"] != "Rendimento médio da produção":
            raise ValueError("A resposta SIDRA não é a variável de rendimento médio.")
        if _normalize_header(str(record["MN"])) != "QUILOGRAMAS POR HECTARE":
            raise ValueError("Unidade inesperada para rendimento médio SIDRA.")
        value_text = str(record["V"]).strip()
        if value_text in {"-", "...", "..", "X", ""}:
            value = np.nan
        elif re.fullmatch(r"-?\d+(?:[.,]\d+)?", value_text):
            value = float(value_text.replace(",", "."))
        else:
            raise ValueError("Rendimento SIDRA não numérico ou não finito.")
        if not re.fullmatch(r"\d{4}", str(record["D3C"])) or str(record["D3N"]) != str(record["D3C"]):
            raise ValueError("Período SIDRA inválido.")
        geography_name = str(record["D1N"])
        municipality = None
        state = None
        if level == "municipio":
            match = re.fullmatch(r"(.+) - ([A-Z]{2})", geography_name)
            if not match:
                raise ValueError(f"Identificação municipal SIDRA inválida: {geography_name}")
            municipality, state = match.groups()
        rows.append(
            {
                "codigo_geografico": str(record["D1C"]),
                "geografia": geography_name,
                "municipio": municipality,
                "uf": state,
                "nivel_geografico": "municipio" if level == "municipio" else "brasil",
                "codigo_cultura": str(record["D4C"]),
                "cultura": str(record["D4N"]),
                "ano": int(record["D3C"]),
                "rendimento_kg_ha": value,
                "unidade": "kg/ha",
            }
        )
    frame = pd.DataFrame(rows, columns=SIDRA_OUTPUT_COLUMNS)
    return _sidra_frame(frame)


def importar_sidra(
    output_dir: Path = OFFICIAL_DATA_DIR,
    municipal_year: int = SIDRA_END_YEAR,
    national_content: bytes | None = None,
    municipal_content: bytes | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Obtém séries nacionais e um recorte municipal, ou importa conteúdo fornecido."""
    if type(municipal_year) is not int or not SIDRA_START_YEAR <= municipal_year <= SIDRA_END_YEAR:
        raise ValueError("Ano municipal SIDRA fora do período suportado.")
    crop_codes = ",".join(SIDRA_CROPS)
    national_url = (
        f"{SIDRA_API}/t/1612/n1/1/v/112/p/"
        f"{SIDRA_START_YEAR}-{SIDRA_END_YEAR}/c81/{crop_codes}"
    )
    municipal_url = f"{SIDRA_API}/t/1612/n6/all/v/112/p/{municipal_year}/c81/{crop_codes}"
    national_bytes = national_content if national_content is not None else _download(national_url)
    municipal_bytes = municipal_content if municipal_content is not None else _download(municipal_url)
    national = parse_sidra_json(national_bytes, "brasil")
    municipalities = parse_sidra_json(municipal_bytes, "municipio")
    expected = {(code, year) for code in SIDRA_CROPS for year in range(SIDRA_START_YEAR, SIDRA_END_YEAR + 1)}
    if set(zip(national["codigo_cultura"], national["ano"])) != expected:
        raise ValueError("Cobertura nacional SIDRA diferente da consulta 1990–2025/culturas.")
    if municipalities["ano"].ne(municipal_year).any() or set(municipalities["codigo_cultura"]) != set(SIDRA_CROPS):
        raise ValueError("Período ou culturas municipais SIDRA diferentes da consulta.")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    national_path = output_dir / SIDRA_NATIONAL_CSV.name
    municipal_path = output_dir / f"sidra1612_rendimento_municipios_{municipal_year}.csv"
    national_bytes_csv = national.to_csv(index=False).encode("utf-8")
    municipal_bytes_csv = municipalities.to_csv(index=False).encode("utf-8")
    metadata = {
        "fonte": "IBGE, Sistema IBGE de Recuperação Automática (SIDRA), tabela 1612",
        "consulta_nacional": national_url,
        "consulta_municipal": municipal_url,
        "variavel": "112 — Rendimento médio da produção",
        "unidade": "quilogramas por hectare",
        "culturas": SIDRA_CROPS,
        "periodo_nacional": f"{SIDRA_START_YEAR}-{SIDRA_END_YEAR}",
        "periodo_municipal": municipal_year,
        "observacoes_nacionais": int(len(national)),
        "observacoes_municipais": int(len(municipalities)),
        "arquivo_fonte_nacional_sha256": _sha256_bytes(national_bytes),
        "arquivo_fonte_municipal_sha256": _sha256_bytes(municipal_bytes),
        "arquivo_nacional_sha256": _sha256_bytes(national_bytes_csv),
        "arquivo_municipal_sha256": _sha256_bytes(municipal_bytes_csv),
        "separacao": "estatísticas agrícolas oficiais; nunca combinadas com linhas IoT",
        "limitacoes": [
            "Rendimento municipal agregado não é produtividade da propriedade.",
            "Ausência no SIDRA é mantida como ausente; não imputada.",
        ],
        "atualizado_em_utc": datetime.now(timezone.utc).isoformat(),
    }
    metadata_bytes = json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    files = {
        national_path: national_bytes_csv,
        municipal_path: municipal_bytes_csv,
        output_dir / f"sidra1612_metadata_municipios_{municipal_year}.json": metadata_bytes,
    }
    if municipal_year == SIDRA_END_YEAR:
        files[output_dir / SIDRA_METADATA.name] = metadata_bytes
    with data_directory(output_dir):
        # A série nacional é compartilhada. Atualizar todos os metadados que a
        # referenciam no mesmo conjunto evita invalidar recortes de outros anos.
        for previous_path in output_dir.glob("sidra1612_metadata*.json"):
            if previous_path in files:
                continue
            previous = _load_metadata(previous_path, "SIDRA")
            previous_municipal = output_dir / f"sidra1612_rendimento_municipios_{previous['periodo_municipal']}.csv"
            if (_sha256_file(previous_municipal) != previous["arquivo_municipal_sha256"]
                    or not national_path.is_file() or _sha256_file(national_path) != previous["arquivo_nacional_sha256"]):
                raise ValueError("Conjunto SIDRA anterior inconsistente; atualização recusada.")
            previous["arquivo_nacional_sha256"] = metadata["arquivo_nacional_sha256"]
            previous["arquivo_fonte_nacional_sha256"] = metadata["arquivo_fonte_nacional_sha256"]
            previous["observacoes_nacionais"] = len(national)
            files[previous_path] = json.dumps(previous, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
        publish_files(files, locked=True)
    return national, municipalities, metadata


def _load_metadata(path: Path, source: str) -> dict[str, Any]:
    try:
        metadata = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError("Schema de metadados incompatível.")
        if source in {"NOAA", "INMET"}:
            required = {"fonte", "url", "arquivo_normalizado", "arquivo_normalizado_sha256",
                        "observacoes", "latitude", "longitude", "inicio_utc", "fim_utc",
                        "unidades", "tratamento", "limitacoes"}
            required |= {"estacao", "wban", "arquivo_fonte_sha256"} if source == "NOAA" else {"station", "station_code", "uf", "arquivo_estacao_sha256"}
            if not required.issubset(metadata):
                raise ValueError("Schema de metadados meteorológicos incompleto.")
            if (type(metadata["observacoes"]) is not int or metadata["observacoes"] <= 0
                    or any(type(metadata[key]) not in {int, float} for key in ["latitude", "longitude"])
                    or not np.isfinite([metadata["latitude"], metadata["longitude"]]).all()
                    or not isinstance(metadata["unidades"], dict)
                    or not all(isinstance(metadata[key], list) and all(isinstance(item, str) for item in metadata[key]) for key in ["tratamento", "limitacoes"])):
                raise ValueError("Tipos dos metadados meteorológicos inválidos.")
            units = {"temperatura_ar": "°C", "precipitacao": "mm por hora", "umidade_relativa_ar": "%"}
            if source == "NOAA":
                units.update(umidade_volumetrica_solo="m³/m³", temperatura_solo="°C")
            if metadata["unidades"] != units:
                raise ValueError("Unidades dos metadados meteorológicos incompatíveis.")
            string_fields = required - {"observacoes", "latitude", "longitude", "unidades", "tratamento", "limitacoes", "wban"}
            if any(not isinstance(metadata[key], str) or not metadata[key].strip() for key in string_fields):
                raise ValueError("Tipos dos metadados meteorológicos inválidos.")
        else:
            required = {"fonte", "consulta_nacional", "consulta_municipal", "variavel", "unidade", "culturas",
                        "periodo_nacional", "periodo_municipal", "observacoes_nacionais", "observacoes_municipais",
                        "arquivo_nacional_sha256", "arquivo_municipal_sha256"}
            if (not required.issubset(metadata) or metadata["periodo_nacional"] != "1990-2025"
                    or type(metadata["periodo_municipal"]) is not int or not 1990 <= metadata["periodo_municipal"] <= 2025
                    or metadata["culturas"] != SIDRA_CROPS
                    or any(type(metadata[key]) is not int or metadata[key] <= 0 for key in ["observacoes_nacionais", "observacoes_municipais"])):
                raise ValueError("Schema de metadados SIDRA incompatível.")
            if metadata["variavel"] != "112 — Rendimento médio da produção" or metadata["unidade"] != "quilogramas por hectare":
                raise ValueError("Variável ou unidade dos metadados SIDRA incompatível.")
            string_fields = required - {"culturas", "periodo_municipal", "observacoes_nacionais", "observacoes_municipais"}
            if any(not isinstance(metadata[key], str) or not metadata[key].strip() for key in string_fields):
                raise ValueError("Tipos dos metadados SIDRA inválidos.")
        for key in required:
            if key.endswith("sha256") and not re.fullmatch(r"[a-fA-F0-9]{64}", str(metadata[key])):
                raise ValueError("Hash de metadados inválido.")
        return metadata
    except (TypeError, KeyError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Metadados locais inválidos; restaure ou importe novamente.") from error


def _local_csv(path: Path, source: str, metadata_path: Path | None = None, *, locked: bool = False) -> pd.DataFrame:
    path = Path(path)
    with nullcontext() if locked else data_directory(path.parent):
        if not path.is_file():
            raise FileNotFoundError(f"Dados {source} não disponíveis localmente; execute a importação.")
        content = path.read_bytes()
        if source in {"NOAA", "INMET"}:
            candidate = Path(metadata_path) if metadata_path is not None else path.with_name(path.stem + "_metadata.json")
            if candidate.parent.resolve() != path.parent.resolve():
                raise ValueError("CSV e metadados devem compartilhar o diretório de publicação.")
            if candidate.is_file():
                metadata = _load_metadata(candidate, source)
                if (metadata.get("arquivo_normalizado") != path.name
                        or metadata.get("arquivo_normalizado_sha256") != _sha256_bytes(content)):
                    raise ValueError("Integridade do conjunto oficial CSV/metadados divergente.")
            elif metadata_path is not None or path.name in {NOAA_CSV.name, INMET_CSV.name}:
                raise ValueError("Metadados oficiais ausentes; restaure ou importe novamente.")
        elif path.name.startswith("sidra1612_rendimento_"):
            if path.name == SIDRA_NATIONAL_CSV.name:
                candidates = list(path.parent.glob("sidra1612_metadata*.json"))
                hash_key = "arquivo_nacional_sha256"
            else:
                match = re.fullmatch(r"sidra1612_rendimento_municipios_(\d{4})\.csv", path.name)
                candidates = [path.parent / f"sidra1612_metadata_municipios_{match[1]}.json"] if match else []
                hash_key = "arquivo_municipal_sha256"
            if not candidates:
                raise ValueError("Metadados SIDRA ausentes.")
            for candidate in candidates:
                metadata = _load_metadata(candidate, "SIDRA")
                if metadata.get(hash_key) != _sha256_bytes(content):
                    raise ValueError("Integridade do conjunto SIDRA CSV/metadados divergente.")
        try:
            return pd.read_csv(io.BytesIO(content))
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"CSV {source} inválido; restaure ou importe novamente.") from error


def carregar_noaa(path: Path = NOAA_CSV, metadata_path: Path | None = None) -> pd.DataFrame:
    return _weather_frame(_local_csv(path, "NOAA", metadata_path), "NOAA")


def carregar_inmet(path: Path = INMET_CSV, metadata_path: Path | None = None) -> pd.DataFrame:
    return _weather_frame(_local_csv(path, "INMET", metadata_path), "INMET")


def carregar_sidra(path: Path = SIDRA_NATIONAL_CSV, *, _locked: bool = False) -> pd.DataFrame:
    frame = _sidra_frame(_local_csv(path, "SIDRA", locked=_locked))
    path = Path(path)
    if path.name == SIDRA_NATIONAL_CSV.name:
        expected = {(code, year) for code in SIDRA_CROPS for year in range(SIDRA_START_YEAR, SIDRA_END_YEAR + 1)}
        if (frame["nivel_geografico"].ne("brasil").any()
                or set(zip(frame["codigo_cultura"], frame["ano"])) != expected):
            raise ValueError("Cobertura nacional SIDRA incompatível.")
    match = re.fullmatch(r"sidra1612_rendimento_municipios_(\d{4})\.csv", path.name)
    if match and (frame["nivel_geografico"].ne("municipio").any() or frame["ano"].ne(int(match[1])).any()):
        raise ValueError("Período ou nível municipal SIDRA incompatível.")
    return frame


def carregar_conjunto_meteorologico(source: str, path: Path | None = None, metadata_path: Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Lê CSV e proveniência da mesma geração sob uma única trava cooperativa."""
    if source not in {"NOAA", "INMET"}:
        raise ValueError("Fonte meteorológica não suportada.")
    path = Path(path) if path is not None else (NOAA_CSV if source == "NOAA" else INMET_CSV)
    metadata_path = Path(metadata_path) if metadata_path is not None else path.with_name(path.stem + "_metadata.json")
    with data_directory(path.parent):
        frame = _weather_frame(_local_csv(path, source, metadata_path, locked=True), source)
        metadata = _load_metadata(metadata_path, source)
        times = pd.to_datetime([metadata["inicio_utc"], metadata["fim_utc"]], format="mixed", utc=True, errors="coerce")
        if (metadata["observacoes"] != len(frame) or times.isna().any()
                or times[0] != frame["timestamp_utc"].min() or times[1] != frame["timestamp_utc"].max()
                or not np.isclose(float(metadata["latitude"]), frame["latitude"].iloc[0], atol=0.000001)
                or not np.isclose(float(metadata["longitude"]), frame["longitude"].iloc[0], atol=0.000001)):
            raise ValueError("Metadados meteorológicos divergem das observações.")
        if source == "NOAA" and (metadata["estacao"] != "GA Newton 11 SW" or str(metadata["wban"]) != "63829" or metadata["url"] != NOAA_URL):
            raise ValueError("Identidade da fonte NOAA incompatível.")
        if source == "INMET" and (metadata["station"] != "SAO PAULO - MIRANTE" or metadata["station_code"] != "A701" or metadata["uf"] != "SP"):
            raise ValueError("Identidade da fonte INMET incompatível.")
        return frame, metadata


def carregar_conjunto_sidra(output_dir: Path = OFFICIAL_DATA_DIR, municipal_year: int = SIDRA_END_YEAR) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Lê as duas escalas SIDRA e os metadados da mesma geração de arquivos."""
    output_dir = Path(output_dir)
    if type(municipal_year) is not int or not SIDRA_START_YEAR <= municipal_year <= SIDRA_END_YEAR:
        raise ValueError("Ano municipal SIDRA fora do período suportado.")
    with data_directory(output_dir):
        national = carregar_sidra(output_dir / SIDRA_NATIONAL_CSV.name, _locked=True)
        municipal = carregar_sidra(output_dir / f"sidra1612_rendimento_municipios_{municipal_year}.csv", _locked=True)
        metadata = _load_metadata(output_dir / f"sidra1612_metadata_municipios_{municipal_year}.json", "SIDRA")
        if (metadata["periodo_municipal"] != municipal_year or metadata["observacoes_nacionais"] != len(national)
                or metadata["observacoes_municipais"] != len(municipal)):
            raise ValueError("Metadados SIDRA divergem das observações.")
        return national, municipal, metadata


def preparar_serie_noaa_diaria(
    frame: pd.DataFrame, depth_column: str
) -> pd.DataFrame:
    """Agrega observações horárias válidas em médias diárias, sem imputação."""
    if depth_column not in {
        "soil_moisture_5cm_m3_m3",
        "soil_moisture_10cm_m3_m3",
        "soil_moisture_20cm_m3_m3",
        "soil_moisture_50cm_m3_m3",
        "soil_moisture_100cm_m3_m3",
    }:
        raise ValueError(f"Profundidade NOAA não suportada: {depth_column}")
    observations = frame[["timestamp_utc", depth_column]].dropna().copy()
    if observations.empty:
        raise ValueError(f"Sem observações válidas para {depth_column}.")
    observations["dia_utc"] = observations["timestamp_utc"].dt.floor("D")
    daily = (
        observations.groupby("dia_utc", as_index=False)
        .agg(
            umidade_media_m3_m3=(depth_column, "mean"),
            n_observacoes=(depth_column, "count"),
        )
        .sort_values("dia_utc")
        .reset_index(drop=True)
    )
    return daily


def preparar_serie_inmet_diaria(
    frame: pd.DataFrame, variable: str
) -> pd.DataFrame:
    allowed = {
        "air_temperature_c": "mean",
        "precipitation_mm": "sum",
        "relative_humidity_pct": "mean",
    }
    if variable not in allowed:
        raise ValueError(f"Variável INMET não suportada: {variable}")
    observations = frame[["timestamp_utc", variable]].dropna().copy()
    if observations.empty:
        raise ValueError(f"Sem observações INMET válidas para {variable}.")
    observations["dia_utc"] = observations["timestamp_utc"].dt.floor("D")
    return (
        observations.groupby("dia_utc", as_index=False)
        .agg(valor=(variable, allowed[variable]))
        .sort_values("dia_utc")
        .reset_index(drop=True)
    )


def preparar_historico_sidra(frame: pd.DataFrame, crop_code: str) -> pd.DataFrame:
    """Prepara apenas observações nacionais oficiais para o gráfico temporal."""
    history = frame.loc[
        (frame["nivel_geografico"] == "brasil")
        & (frame["codigo_cultura"].astype(str) == str(crop_code)),
        ["ano", "rendimento_kg_ha"],
    ].dropna(subset=["rendimento_kg_ha"])
    if history.empty:
        raise ValueError(f"Sem histórico nacional SIDRA para a cultura {crop_code}.")
    return history.sort_values("ano").reset_index(drop=True)
