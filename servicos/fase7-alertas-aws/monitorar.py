"""Monitora previsão ou registros de sensores da Fase 2 e publica com --enviar.

Sem --enviar o comando apenas imprime o e-mail. Não altera a dashboard.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensagem import assunto, corpo
from regras import JANELA_HORAS, avaliar
from sensores import TIPOS_IOT, avaliar_sensor, ler_leitura_csv

PASTA = Path(__file__).resolve().parent
REGISTRO = PASTA / ".ultimo-alerta.json"
INTERVALO_REPETICAO = timedelta(hours=6)


def ler_previsao(caminho):
    bruto = Path(caminho).read_text(encoding="utf-8")
    dados = json.loads(bruto)
    if not isinstance(dados, dict) or dados.get("status") != "ok":
        raise ValueError("O arquivo precisa ser um Result ok da Fase 2.")
    data = dados.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("hourly"), list):
        raise ValueError("O arquivo não contém a série horária da Fase 2.")
    local = data.get("location") if isinstance(data.get("location"), dict) else {}
    return local, data["hourly"]


def consultar_cidade(cidade):
    from farmtech_integracao.fase2 import forecast

    resultado = forecast(cidade)
    if not resultado.ok:
        raise RuntimeError(resultado.message)
    return resultado.data.get("location") or {}, resultado.data.get("hourly") or []


def _chave_cidade(local):
    if local is None:
        return None
    if not isinstance(local, dict) or not isinstance(local.get("name"), str) or not local["name"].strip():
        raise ValueError("A publicação exige a identificação da cidade consultada.")
    campos = ("name", "admin1", "country", "latitude", "longitude")
    if "iot_dispositivo" in local:
        campos += ("iot_dispositivo", "iot_origem")
    return json.dumps([" ".join(str(local.get(campo, "")).split()).casefold()
                       for campo in campos], ensure_ascii=False)


def _ler_registros(agora):
    """Falha explicitamente: estado inválido não equivale a ausência de publicação."""
    try:
        anterior = json.loads(REGISTRO.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        raise RuntimeError("Registro de publicação ilegível ou inválido; corrija-o antes de enviar.") from exc
    try:
        if not isinstance(anterior, dict):
            raise ValueError("Registro deve ser um objeto.")
        registros = anterior.get("registros") if "registros" in anterior else [anterior]
        if not isinstance(registros, list):
            raise ValueError("Histórico deve ser uma lista.")
        validos = []
        for registro in registros:
            if (not isinstance(registro, dict)
                    or registro.get("tipo") not in ({"chuva", "umidade_baixa", "umidade_alta"} | TIPOS_IOT)
                    or not isinstance(registro.get("message_id"), str)
                    or not registro["message_id"].strip()
                    or not isinstance(registro.get("publicado_em"), str)
                    or (registro.get("cidade") is not None
                        and (not isinstance(registro["cidade"], str) or not registro["cidade"].strip()))):
                raise ValueError("Publicação registrada inválida.")
            quando = datetime.fromisoformat(registro["publicado_em"].replace("Z", "+00:00"))
            if quando.tzinfo is None:
                quando = quando.replace(tzinfo=timezone.utc)
            if quando > agora:
                raise ValueError("Publicação registrada no futuro; confira o relógio e o registro.")
            if agora - quando < INTERVALO_REPETICAO:
                validos.append(registro)
        return validos
    except (OSError, ValueError, KeyError, TypeError):
        raise RuntimeError("Registro de publicação inválido ou futuro; confira o relógio e corrija o registro antes de enviar.") from None


def repetido(alerta, agora, local=None):
    cidade = _chave_cidade(local)
    return any(registro["tipo"] == alerta["tipo"]
               and (registro.get("cidade") is None or cidade is None or registro["cidade"] == cidade)
               for registro in _ler_registros(agora))


def gravar_registro(alerta, agora, message_id, local=None):
    registros = _ler_registros(agora)
    registros.append({
        "tipo": alerta["tipo"],
        "cidade": _chave_cidade(local),
        "publicado_em": agora.isoformat(),
        "message_id": message_id,
    })
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=REGISTRO.parent,
                                         prefix=".ultimo-alerta.", suffix=".tmp", delete=False) as arquivo:
            temporario = Path(arquivo.name)
            json.dump({"registros": registros}, arquivo, ensure_ascii=False)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, REGISTRO)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Alerta FarmTech a partir de sensores ou previsão da Fase 2.")
    origem = parser.add_mutually_exclusive_group(required=True)
    origem.add_argument("--cidade", help="Cidade consultada na Fase 2, por exemplo Irecê.")
    origem.add_argument("--arquivo", help="JSON de um Result ok já obtido, sem consultar a rede.")
    origem.add_argument("--iot-csv", help="CSV original de 11 campos do coletor de sensores da Fase 2.")
    parser.add_argument("--origem-iot", choices=("wokwi", "esp32", "desconhecida", "exemplo"),
                        default="desconhecida", help="Origem declarada; o CSV não comprova sua proveniência.")
    parser.add_argument("--fuso-iot", help="UTC ou offset como -03:00 para horários do PC sem fuso.")
    parser.add_argument("--local-iot", help="Identificação do local, declarada pelo operador.")
    parser.add_argument("--dispositivo-iot", help="Identificação do dispositivo/simulador, declarada pelo operador.")
    parser.add_argument("--historico-iot", action="store_true", help="Reprodução histórica, exclusiva para dry-run.")
    parser.add_argument("--horas", type=int, default=JANELA_HORAS)
    parser.add_argument("--enviar", action="store_true", help="Publica no SNS. Sem esta opção, só imprime.")
    args = parser.parse_args(argv)
    if args.arquivo and args.enviar:
        parser.error("--arquivo é exclusivo para testes locais; --enviar exige --cidade e previsão consultada.")
    if not args.iot_csv and (args.origem_iot != "desconhecida" or args.fuso_iot is not None
                             or args.local_iot is not None or args.dispositivo_iot is not None
                             or args.historico_iot):
        parser.error("As opções IoT exigem --iot-csv.")
    if args.iot_csv and args.horas != JANELA_HORAS:
        parser.error("--horas configura somente a previsão; sensores usam idade máxima de cinco minutos.")
    if args.iot_csv and args.enviar:
        if args.historico_iot or args.origem_iot not in {"wokwi", "esp32"}:
            parser.error("Histórico, exemplo e origem desconhecida são exclusivos para dry-run IoT.")
        if not (args.local_iot and args.local_iot.strip()
                and args.dispositivo_iot and args.dispositivo_iot.strip()):
            parser.error("O envio IoT exige --local-iot e --dispositivo-iot explícitos.")

    if args.iot_csv:
        leitura = ler_leitura_csv(args.iot_csv, fuso=args.fuso_iot)
        if args.enviar and leitura["_sintetico"]:
            parser.error("Exemplo IoT sintético não pode ser publicado, independentemente da origem declarada.")
        alerta = avaliar_sensor(leitura, origem=args.origem_iot, historico=args.historico_iot)
        local = {"name": args.local_iot or "local IoT não informado",
                 "iot_dispositivo": args.dispositivo_iot or "não informado",
                 "iot_origem": "exemplo" if leitura["_sintetico"] else args.origem_iot}
        if alerta is None:
            modo = "reprodução histórica" if args.historico_iot else "registro recente de recepção no PC"
            fonte = {"exemplo": "exemplo sintético", "wokwi": "simulação Wokwi declarada",
                     "esp32": "captura ESP32 declarada, não verificada",
                     "desconhecida": "origem não comprovada"}[
                         "exemplo" if leitura["_sintetico"] else args.origem_iot]
            print(f"Sem alerta IoT nos critérios didáticos. Modo: {modo}; origem: {fonte}. Nada foi publicado.")
            return 0
    elif args.arquivo:
        local, hourly = ler_previsao(args.arquivo)
        alerta = avaliar(hourly, horas=args.horas)
    else:
        local, hourly = consultar_cidade(args.cidade)
        alerta = avaliar(hourly, horas=args.horas)

    if alerta is None:
        print("Sem alerta. Nenhum limiar da janela foi cruzado. Nada foi publicado.")
        return 0

    texto_assunto = assunto(alerta)
    texto_corpo = corpo(alerta, local)
    print(texto_assunto)
    print(texto_corpo)

    if not args.enviar:
        print("\nModo local: a mensagem não foi enviada. Use --enviar na EC2 para publicar.")
        return 0

    agora = datetime.now(timezone.utc)
    if repetido(alerta, agora, local):
        print("\nO mesmo alerta para esta cidade já foi publicado nas últimas 6 horas. Nova publicação recusada.")
        return 0

    from publicar_sns import publicar

    message_id = publicar(alerta, local, assunto=texto_assunto, corpo=texto_corpo)
    try:
        gravar_registro(alerta, agora, message_id, local)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(f"SNS confirmou a publicação. MessageId: {message_id}. "
                           "Falha ao gravar o controle de repetição; não repita o envio automaticamente. "
                           "Reconcilie o registro antes da próxima execução.") from exc
    print(f"\nPublicado no SNS. MessageId: {message_id}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
