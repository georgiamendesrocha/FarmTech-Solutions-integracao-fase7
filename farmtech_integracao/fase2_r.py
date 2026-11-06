"""Validação explícita da Fase 2 em R; nunca substitui os dados históricos.

Executa os scripts R preservados em um sandbox temporário:
- app.r iot: estatísticas do CSV histórico original, em cópia isolada;
- 02_integrar_previsao.R: integração de dois CSVs inteiramente sintéticos,
  com horários compatíveis e resultados conhecidos, para teste reproduzível.
O CSV meteorológico real e os CSVs históricos do projeto nunca são modificados.
"""
from __future__ import annotations

import csv
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .runtime import PROJECT_ROOT, SERVICE_DIRS

F2 = SERVICE_DIRS["fase2"]
EXPORT_DIR = PROJECT_ROOT / ".runtime" / "exports" / "fase2"


def localizar_rscript() -> Path | None:
    """Localiza Rscript pelo PATH, configuração explícita ou pastas padrão do Windows."""
    configured = os.environ.get("FARMTECH_RSCRIPT", "").strip().strip('"')
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return candidate.resolve()
    located = shutil.which("Rscript") or shutil.which("Rscript.exe")
    if located:
        return Path(located).resolve()
    if os.name == "nt":
        directories = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "R",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "R",
        ]
        candidates: list[Path] = []
        for directory in directories:
            if directory.is_dir():
                for install in directory.glob("R-*"):
                    for rel in ("bin/Rscript.exe", "bin/x64/Rscript.exe"):
                        candidate = install / rel
                        if candidate.is_file():
                            candidates.append(candidate)
        # As instalações comuns R-X.Y.Z são ordenáveis por versão.
        def version(path: Path) -> tuple[int, ...]:
            import re
            found = re.findall(r"\d+", path.parent.parent.name)
            if path.parent.name == "x64":
                found = re.findall(r"\d+", path.parent.parent.parent.name)
            return tuple(map(int, found)) if found else (0,)
        if candidates:
            return max(candidates, key=version).resolve()
    return None


def _csv_string(headers: list[str], rows: list[list[str | int | float]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue()


def _demo_inputs(root: Path) -> None:
    # Datas sintéticas fixas, dentro do intervalo dos dados de previsão sintéticos.
    # Nenhuma linha é declarada como medição real da propriedade.
    sensors = _csv_string(
        ["ts_iso", "t_rel_ms", "umidade", "temp_c", "ldr", "ph_base", "ph_corr", "N", "P", "K", "bomba_fw"],
        [
            ["2026-05-03T20:00:00Z", 1000, 40, 22, 800, 6.2, 6.4, 1, 0, 1, 1],
            ["2026-05-03T20:30:00Z", 2000, 50, 23, 810, 6.3, 6.5, 1, 1, 1, 1],
            ["2026-05-03T21:00:00Z", 3000, 60, 24, 820, 6.4, 6.6, 1, 1, 1, 0],
        ],
    )
    forecast = _csv_string(
        ["city", "country", "latitude", "longitude", "ts_iso", "temp_c", "umidade", "rain_mm", "wind_ms", "weathercode"],
        [
            ["Cidade demonstrativa (sintética)", "Brasil", -11.3, -41.9, "2026-05-03T20:00:00Z", 20, 60, 0, 1, 0],
            ["Cidade demonstrativa (sintética)", "Brasil", -11.3, -41.9, "2026-05-03T21:00:00Z", 24, 70, 2, 3, 1],
        ],
    )
    sensor_file = root / "dados" / "historico_irrigacao.csv"
    weather_file = root / "dados" / "previsao_tempo" / "previsao_tempo.csv"
    sensor_file.parent.mkdir(parents=True, exist_ok=True)
    weather_file.parent.mkdir(parents=True, exist_ok=True)
    sensor_file.write_text(sensors, encoding="utf-8")
    weather_file.write_text(forecast, encoding="utf-8")


def _execute(rscript: Path, script: Path, cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        [str(rscript), "--vanilla", str(script), *args],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=90, check=False,
        env={**os.environ, "R_DEFAULT_PACKAGES": "utils,stats,graphics,grDevices,methods,datasets"},
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "sem mensagem de erro").strip()
        # Retém apenas o trecho final, suficiente para diagnosticar sintaxe ou dependência.
        details = " | ".join(details.splitlines()[-3:])[-700:]
        raise RuntimeError(f"O script {script.name} encerrou com erro: {details}")
    return completed.stdout


def _validate_demo_csv(path: Path) -> tuple[str, list[dict[str, str]]]:
    if not path.is_file():
        raise RuntimeError("O R não produziu o CSV integrado demonstrativo.")
    content = path.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(content)))
    if len(rows) != 3:
        raise RuntimeError("O CSV integrado não contém os três registros demonstrativos esperados.")
    checks = {
        "forecast_temp_c": [20, 22, 24],
        "forecast_umidade": [60, 65, 70],
        "forecast_rain_mm": [0, 1, 2],
        "forecast_wind_ms": [1, 2, 3],
    }
    for column, expected in checks.items():
        try:
            actual = [float(row[column]) for row in rows]
        except (KeyError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Saída R inválida para {column}.") from exc
        if any(abs(a-b) > 1e-8 for a, b in zip(actual, expected)):
            raise RuntimeError(f"A interpolação calculada pelo R não corresponde ao cenário de referência: {column}.")
    if not all("demonstrativa" in row.get("forecast_city", "") for row in rows):
        raise RuntimeError("O CSV integrado perdeu a identificação da origem demonstrativa.")
    return content, rows


def validar_fase2_r() -> dict:
    """Executa ambas as etapas R; só retorna 'ok' após verificar os arquivos e cálculos."""
    rscript = localizar_rscript()
    if rscript is None:
        return {"status": "unavailable", "message": "Rscript não encontrado. Instale R ou defina FARMTECH_RSCRIPT."}
    original = F2 / "dados" / "historico_irrigacao.csv"
    app = F2 / "app.r"
    integrate = F2 / "r" / "02_integrar_previsao.R"
    helper = F2 / "r" / "temporal_utils.R"
    missing = [p.name for p in (original, app, integrate, helper) if not p.is_file()]
    if missing:
        return {"status": "unavailable", "message": "Arquivos da Fase 2 ausentes: " + ", ".join(missing)}
    workspace = PROJECT_ROOT / ".runtime" / "fase2" / "r_validacao"
    workspace.mkdir(parents=True, exist_ok=True)
    import hashlib
    digest_before = hashlib.sha256(original.read_bytes()).hexdigest()
    try:
        with tempfile.TemporaryDirectory(prefix="r_fase2_", dir=workspace) as temporary:
            workspace_root = Path(temporary)
            # Repete a estrutura do serviço dentro da área temporária, isolando saídas.
            real = workspace_root / "historico" / "servicos" / "fase2-iot"
            real_sensor = real / "dados" / "historico_irrigacao.csv"
            real_sensor.parent.mkdir(parents=True)
            shutil.copy2(original, real_sensor)
            _execute(rscript, app, real, "iot")
            report_path = real / "dados" / "analises" / "iot" / "analise_historico.txt"
            history_csv = real / "dados" / "analises" / "iot" / "analise_historico.csv"
            if not report_path.is_file() or not history_csv.is_file():
                raise RuntimeError("A análise R do histórico não gerou relatório e CSV.")
            with history_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                history_rows = sum(1 for _ in csv.DictReader(handle))
            if history_rows < 1:
                raise RuntimeError("A análise do histórico R retornou um CSV vazio.")
            history_report = report_path.read_text(encoding="utf-8-sig", errors="replace")

            demo = workspace_root / "demonstracao" / "servicos" / "fase2-iot"
            _demo_inputs(demo)
            _execute(rscript, integrate, demo)
            demo_csv = demo / "dados" / "analises" / "integrada" / "dados_integrados_iot_previsao.csv"
            content, rows = _validate_demo_csv(demo_csv)

            digest_after = hashlib.sha256(original.read_bytes()).hexdigest()
            if digest_before != digest_after:
                raise RuntimeError("A integridade do CSV histórico foi alterada.")
            # Resultados são publicados exclusivamente na pasta descartável de execução.
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            import uuid
            for filename, body in (
                ("validacao_r_demonstrativa.csv", content),
                ("analise_r_historico.txt", history_report),
            ):
                destination = EXPORT_DIR / filename
                temp = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
                try:
                    temp.write_text(body, encoding="utf-8")
                    os.replace(temp, destination)
                finally:
                    temp.unlink(missing_ok=True)
            return {
                "status": "ok",
                "message": "Rscript executou a análise do histórico IoT e integrou dados sintéticos; cálculos e arquivos de saída validados.",
                "historico_linhas": history_rows,
                "demonstracao_linhas": len(rows),
                "amostra": rows,
                "csv_demonstrativo": content,
                "relatorio_historico": history_report,
                "origem": "Histórico IoT preservado; integração entre dois datasets sintéticos temporalmente compatíveis.",
                "rscript": rscript.name,
                "csv_original_preservado": True,
            }
    except subprocess.TimeoutExpired:
        message = "Execução R excedeu o limite de 90 segundos. Os dados históricos permanecem preservados."
    except (RuntimeError, OSError, ValueError, UnicodeError) as err:
        message = str(err)
    return {"status": "error", "message": message}
