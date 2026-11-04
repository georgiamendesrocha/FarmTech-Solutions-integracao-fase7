"""Carga restrita de pickle/joblib com referências revisadas no código.

Hashes detectam substituição dos artefatos, não autenticam quem possa alterar também
este código. O diretório e o código precisam permanecer sob controle do operador.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

from src.validation import validar_entrada_original, validar_entrada_ph


ORIGINAL_COMMIT = "d0a916858590c89ab8812baf1c45d48f923f0566"
# Conferidos na Etapa A contra blobs do commit no repositório original.
ORIGINAL_HASHES = {
    "rainfall": "6fe9f2afc508254b85f184b6345da5b0aa8301b0423b2dc927671d6d2e01a75c",
    "humidity": "ffffce2e370fa7d19061337f364dd97235f3a10c477e1add1016735aa213c9f9",
}
RESIDUAL_HASHES = {
    "rainfall": "8b4740b48a59e96998856b0c385e510e9477fa2190b62910ec313620d81f2130",
    "humidity": "15108458e6caa12b7ef313dc236733248772abc324ebf9a274bd24f8844c835c",
}
DATASET_SHA256 = "54a5a6e5408668e668667efc50de2fc867c1b875e0431b4f54dd331b0a109a4e"
PH_SHA256 = "0ab712d8a4765a4fddcac4315e9803b9df2e4f8a1e5f1efc789f2e5974166625"
VALIDATED_SKLEARN = "1.6.1"
HISTORICAL_COMPATIBILITY = (
    "Artefatos históricos serializados com scikit-learn 1.9.0: uso restrito ao "
    "runtime 1.6.1 após conferência de integridade e reprodução de 440 previsões. "
    "Esta mitigação não constitui compatibilidade entre versões suportada pelo scikit-learn."
)


class HistoricalCompatibilityWarning(UserWarning):
    """Compatibilidade limitada aos artefatos e aos cenários de referência."""


# Só artefatos criados por este processo podem ser confiados fora do pacote.
# Não importamos confiança de JSON colocado ao lado de um pickle desconhecido.
_locally_generated: dict[Path, str] = {}


def registrar_artefato_gerado(path: Path) -> None:
    path = Path(path).resolve()
    _locally_generated[path] = hashlib.sha256(path.read_bytes()).hexdigest()


def bytes_verificados(path: Path, expected: str, mensagem: str) -> bytes:
    try:
        payload = Path(path).read_bytes()
    except OSError as error:
        raise RuntimeError("Arquivo necessário ao modelo indisponível.") from error
    if hashlib.sha256(payload).hexdigest() != expected:
        raise RuntimeError(mensagem)
    return payload


def carregar_json(path: Path) -> dict:
    def reject_constant(value):
        raise ValueError("Constante JSON não finita.")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Chave JSON duplicada.")
            result[key] = value
        return result

    def validate_numbers(value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Número JSON não finito.")
        if isinstance(value, dict):
            for item in value.values():
                validate_numbers(item)
        elif isinstance(value, list):
            for item in value:
                validate_numbers(item)

    try:
        result = json.loads(
            Path(path).read_text(encoding="utf-8"), parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
        validate_numbers(result)
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError("Arquivo de diagnóstico indisponível ou inválido.") from error
    if not isinstance(result, dict):
        raise ValueError("Schema do arquivo de diagnóstico inválido.")
    return result


def carregar_joblib_verificado(path: Path, expected: str):
    payload = bytes_verificados(path, expected, "Integridade do modelo inválida; carga recusada.")
    try:
        # Os bytes verificados são os mesmos desserializados (sem janela TOCTOU).
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", InconsistentVersionWarning)
            model = joblib.load(BytesIO(payload))
    except Exception as error:
        raise RuntimeError("Não foi possível carregar o modelo verificado.") from error
    version_warnings = []
    for item in caught:
        if issubclass(item.category, InconsistentVersionWarning):
            version_warnings.append(str(item.message))
        else:
            warnings.warn(item.message, item.category, stacklevel=2)
    return model, version_warnings


def hash_confiavel_ph(path: Path, packaged_path: Path) -> str:
    if Path(path).resolve() == Path(packaged_path).resolve():
        return PH_SHA256
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() == PH_SHA256:
        return PH_SHA256  # Uma cópia exata tem os mesmos bytes já revisados.
    digest = _locally_generated.get(Path(path).resolve())
    if digest is None:
        raise RuntimeError("Modelo externo sem procedência verificada; carga recusada.")
    return digest


class ModeloValidado:
    """Valida o contrato também para consumidores Python fora do formulário."""

    def __init__(self, model, tipo: str, diagnostico: dict):
        self._model = model
        self._tipo = tipo
        self.diagnostico = diagnostico

    def __getattr__(self, name):
        return getattr(self._model, name)

    def predict(self, frame):
        validator = validar_entrada_ph if self._tipo == "ph" else validar_entrada_original
        if not isinstance(frame, pd.DataFrame) or frame.empty or frame.columns.duplicated().any():
            raise ValueError("Forneça entradas tabulares válidas para a previsão.")
        validated = pd.DataFrame([validator(row) for row in frame.to_dict("records")])
        prediction = np.asarray(self._model.predict(validated), dtype=float)
        if prediction.shape != (len(validated),) or not np.isfinite(prediction).all():
            raise RuntimeError("O modelo não produziu resultados numéricos finitos.")
        if self._tipo == "ph" and ((prediction < 0) | (prediction > 14)).any():
            raise RuntimeError("O modelo produziu pH fora do intervalo físico.")
        return prediction


def validar_runtime() -> None:
    if sklearn.__version__ != VALIDATED_SKLEARN:
        raise RuntimeError("Runtime do modelo não validado. Utilize scikit-learn 1.6.1 e repita o diagnóstico.")
