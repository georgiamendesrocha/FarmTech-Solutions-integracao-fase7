"""Monitora a previsão da Fase 2 e, com --enviar, publica o alerta no SNS.

Sem --enviar o comando apenas imprime o e-mail. Não altera a dashboard.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mensagem import assunto, corpo
from regras import JANELA_HORAS, avaliar

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


def repetido(alerta, agora):
    if not REGISTRO.is_file():
        return False
    try:
        anterior = json.loads(REGISTRO.read_text(encoding="utf-8"))
        quando = datetime.fromisoformat(anterior["publicado_em"])
    except (OSError, ValueError, KeyError, TypeError):
        return False
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return anterior.get("tipo") == alerta["tipo"] and agora - quando < INTERVALO_REPETICAO


def gravar_registro(alerta, agora, message_id):
    REGISTRO.write_text(json.dumps({
        "tipo": alerta["tipo"],
        "publicado_em": agora.isoformat(),
        "message_id": message_id,
    }, ensure_ascii=False), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Alerta FarmTech a partir da previsão da Fase 2.")
    origem = parser.add_mutually_exclusive_group(required=True)
    origem.add_argument("--cidade", help="Cidade consultada na Fase 2, por exemplo Irecê.")
    origem.add_argument("--arquivo", help="JSON de um Result ok já obtido, sem consultar a rede.")
    parser.add_argument("--horas", type=int, default=JANELA_HORAS)
    parser.add_argument("--enviar", action="store_true", help="Publica no SNS. Sem esta opção, só imprime.")
    args = parser.parse_args(argv)

    if args.arquivo:
        local, hourly = ler_previsao(args.arquivo)
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
    if repetido(alerta, agora):
        print("\nO mesmo alerta já foi publicado nas últimas 6 horas. Nova publicação recusada.")
        return 0

    from publicar_sns import publicar

    message_id = publicar(alerta, local, assunto=texto_assunto, corpo=texto_corpo)
    gravar_registro(alerta, agora, message_id)
    print(f"\nPublicado no SNS. MessageId: {message_id}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
